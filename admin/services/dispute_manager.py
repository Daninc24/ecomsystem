"""
Dispute management service for handling order disputes and issue resolution
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from bson import ObjectId

from ..models.order import Dispute, DisputeStatus
from .base_service import BaseService


class DisputeManager(BaseService):
    """Service for managing order disputes and issue resolution."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'disputes'
    
    def create_dispute(self, dispute_data: Dict[str, Any], user_id: ObjectId) -> Dispute:
        """Create a new dispute."""
        dispute = Dispute(**dispute_data)
        dispute.dispute_number = self._generate_dispute_number()
        dispute.created_by = user_id
        
        # Insert into database
        result = self.db.disputes.insert_one(dispute.to_dict())
        dispute.id = result.inserted_id
        
        return dispute
    
    def get_dispute(self, dispute_id: ObjectId) -> Optional[Dispute]:
        """Get dispute by ID."""
        dispute_data = self.db.disputes.find_one({'_id': dispute_id})
        if dispute_data:
            return Dispute.from_dict(dispute_data)
        return None
    
    def get_dispute_by_number(self, dispute_number: str) -> Optional[Dispute]:
        """Get dispute by dispute number."""
        dispute_data = self.db.disputes.find_one({'dispute_number': dispute_number})
        if dispute_data:
            return Dispute.from_dict(dispute_data)
        return None
    
    def get_disputes_by_order(self, order_id: ObjectId) -> List[Dispute]:
        """Get all disputes for an order."""
        disputes_data = self.db.disputes.find({'order_id': order_id})
        return [Dispute.from_dict(dispute_data) for dispute_data in disputes_data]
    
    def get_disputes_by_customer(self, customer_id: ObjectId, limit: int = 50) -> List[Dispute]:
        """Get disputes by customer."""
        disputes_data = self.db.disputes.find({'customer_id': customer_id}).limit(limit)
        return [Dispute.from_dict(dispute_data) for dispute_data in disputes_data]
    
    def get_disputes_by_vendor(self, vendor_id: ObjectId, limit: int = 50) -> List[Dispute]:
        """Get disputes by vendor."""
        disputes_data = self.db.disputes.find({'vendor_id': vendor_id}).limit(limit)
        return [Dispute.from_dict(dispute_data) for dispute_data in disputes_data]
    
    def get_disputes_by_status(self, status: DisputeStatus, limit: int = 100) -> List[Dispute]:
        """Get disputes by status."""
        disputes_data = self.db.disputes.find({'status': status.value}).limit(limit)
        return [Dispute.from_dict(dispute_data) for dispute_data in disputes_data]
    
    def get_open_disputes(self, limit: int = 100) -> List[Dispute]:
        """Get all open disputes that need attention."""
        open_statuses = [DisputeStatus.OPEN.value, DisputeStatus.UNDER_REVIEW.value]
        disputes_data = self.db.disputes.find({'status': {'$in': open_statuses}}).limit(limit)
        return [Dispute.from_dict(dispute_data) for dispute_data in disputes_data]
    
    def update_dispute_status(self, dispute_id: ObjectId, status: DisputeStatus, 
                            user_id: ObjectId) -> bool:
        """Update dispute status."""
        update_data = {
            'status': status.value,
            'updated_at': datetime.utcnow(),
            'updated_by': user_id
        }
        
        # Add resolution date if resolving
        if status in [DisputeStatus.RESOLVED, DisputeStatus.CLOSED]:
            update_data['resolved_date'] = datetime.utcnow()
            update_data['resolved_by'] = user_id
        
        result = self.db.disputes.update_one(
            {'_id': dispute_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    def add_message(self, dispute_id: ObjectId, message_data: Dict[str, Any], 
                   user_id: ObjectId) -> bool:
        """Add a message to a dispute."""
        message = {
            'id': ObjectId(),
            'sender_id': user_id,
            'sender_type': message_data.get('sender_type', 'admin'),  # admin, customer, vendor
            'message': message_data.get('message', ''),
            'timestamp': datetime.utcnow(),
            'is_internal': message_data.get('is_internal', False)
        }
        
        result = self.db.disputes.update_one(
            {'_id': dispute_id},
            {
                '$push': {'messages': message},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0
    
    def add_attachment(self, dispute_id: ObjectId, attachment_data: Dict[str, Any], 
                      user_id: ObjectId) -> bool:
        """Add an attachment to a dispute."""
        attachment = {
            'id': ObjectId(),
            'filename': attachment_data.get('filename', ''),
            'file_path': attachment_data.get('file_path', ''),
            'file_size': attachment_data.get('file_size', 0),
            'mime_type': attachment_data.get('mime_type', ''),
            'uploaded_by': user_id,
            'uploaded_at': datetime.utcnow()
        }
        
        result = self.db.disputes.update_one(
            {'_id': dispute_id},
            {
                '$push': {'attachments': attachment},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0
    
    def resolve_dispute(self, dispute_id: ObjectId, resolution_data: Dict[str, Any], 
                       user_id: ObjectId) -> bool:
        """Resolve a dispute with a resolution."""
        update_data = {
            'status': DisputeStatus.RESOLVED.value,
            'resolution': resolution_data.get('resolution', ''),
            'resolution_amount': resolution_data.get('resolution_amount', 0.0),
            'resolved_date': datetime.utcnow(),
            'resolved_by': user_id,
            'updated_at': datetime.utcnow()
        }
        
        result = self.db.disputes.update_one(
            {'_id': dispute_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Add resolution message
            resolution_message = {
                'message': f"Dispute resolved: {resolution_data.get('resolution', '')}",
                'sender_type': 'admin',
                'is_internal': False
            }
            self.add_message(dispute_id, resolution_message, user_id)
            
            # Process resolution amount if specified
            resolution_amount = resolution_data.get('resolution_amount', 0.0)
            if resolution_amount > 0:
                self._process_resolution_payment(dispute_id, resolution_amount, user_id)
        
        return result.modified_count > 0
    
    def escalate_dispute(self, dispute_id: ObjectId, escalation_reason: str, 
                        user_id: ObjectId) -> bool:
        """Escalate a dispute to higher level support."""
        update_data = {
            'status': DisputeStatus.ESCALATED.value,
            'updated_at': datetime.utcnow(),
            'updated_by': user_id
        }
        
        result = self.db.disputes.update_one(
            {'_id': dispute_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Add escalation message
            escalation_message = {
                'message': f"Dispute escalated: {escalation_reason}",
                'sender_type': 'admin',
                'is_internal': True
            }
            self.add_message(dispute_id, escalation_message, user_id)
        
        return result.modified_count > 0
    
    def close_dispute(self, dispute_id: ObjectId, closing_notes: str, user_id: ObjectId) -> bool:
        """Close a dispute."""
        update_data = {
            'status': DisputeStatus.CLOSED.value,
            'updated_at': datetime.utcnow(),
            'updated_by': user_id
        }
        
        result = self.db.disputes.update_one(
            {'_id': dispute_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0 and closing_notes:
            # Add closing message
            closing_message = {
                'message': f"Dispute closed: {closing_notes}",
                'sender_type': 'admin',
                'is_internal': False
            }
            self.add_message(dispute_id, closing_message, user_id)
        
        return result.modified_count > 0
    
    def search_disputes(self, query: str, filters: Dict[str, Any] = None, 
                       limit: int = 50) -> List[Dispute]:
        """Search disputes by various criteria."""
        search_filter = {}
        
        # Add text search
        if query:
            search_filter['$or'] = [
                {'dispute_number': {'$regex': query, '$options': 'i'}},
                {'subject': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}}
            ]
        
        # Add additional filters
        if filters:
            if 'status' in filters:
                search_filter['status'] = filters['status']
            if 'dispute_type' in filters:
                search_filter['dispute_type'] = filters['dispute_type']
            if 'customer_id' in filters:
                search_filter['customer_id'] = ObjectId(filters['customer_id'])
            if 'vendor_id' in filters:
                search_filter['vendor_id'] = ObjectId(filters['vendor_id'])
            if 'date_from' in filters:
                search_filter['created_at'] = {'$gte': filters['date_from']}
            if 'date_to' in filters:
                if 'created_at' not in search_filter:
                    search_filter['created_at'] = {}
                search_filter['created_at']['$lte'] = filters['date_to']
        
        disputes_data = self.db.disputes.find(search_filter).limit(limit)
        return [Dispute.from_dict(dispute_data) for dispute_data in disputes_data]
    
    def get_dispute_statistics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get dispute statistics for dashboard."""
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Aggregate pipeline for statistics
        pipeline = [
            {'$match': {'created_at': {'$gte': start_date}}},
            {'$group': {
                '_id': None,
                'total_disputes': {'$sum': 1},
                'avg_resolution_time': {'$avg': {
                    '$subtract': ['$resolved_date', '$created_at']
                }},
                'disputes_by_status': {
                    '$push': '$status'
                },
                'disputes_by_type': {
                    '$push': '$dispute_type'
                },
                'total_resolution_amount': {'$sum': '$resolution_amount'}
            }}
        ]
        
        result = list(self.db.disputes.aggregate(pipeline))
        
        if not result:
            return {
                'total_disputes': 0,
                'open_disputes': 0,
                'resolved_disputes': 0,
                'avg_resolution_time_hours': 0,
                'disputes_by_status': {},
                'disputes_by_type': {},
                'total_resolution_amount': 0.0
            }
        
        stats = result[0]
        
        # Process status counts
        status_counts = {}
        for status in stats.get('disputes_by_status', []):
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Process type counts
        type_counts = {}
        for dispute_type in stats.get('disputes_by_type', []):
            type_counts[dispute_type] = type_counts.get(dispute_type, 0) + 1
        
        # Convert resolution time from milliseconds to hours
        avg_resolution_ms = stats.get('avg_resolution_time', 0) or 0
        avg_resolution_hours = avg_resolution_ms / (1000 * 60 * 60) if avg_resolution_ms else 0
        
        return {
            'total_disputes': stats.get('total_disputes', 0),
            'open_disputes': status_counts.get(DisputeStatus.OPEN.value, 0) + 
                           status_counts.get(DisputeStatus.UNDER_REVIEW.value, 0),
            'resolved_disputes': status_counts.get(DisputeStatus.RESOLVED.value, 0),
            'avg_resolution_time_hours': round(avg_resolution_hours, 2),
            'disputes_by_status': status_counts,
            'disputes_by_type': type_counts,
            'total_resolution_amount': stats.get('total_resolution_amount', 0.0)
        }
    
    def _generate_dispute_number(self) -> str:
        """Generate unique dispute number."""
        now = datetime.utcnow()
        date_str = now.strftime('%Y%m%d')
        
        # Get count of disputes today
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        daily_count = self.db.disputes.count_documents({
            'created_at': {'$gte': start_of_day, '$lt': end_of_day}
        })
        
        # Generate dispute number: DSP-YYYYMMDD-NNNN
        return f"DSP-{date_str}-{daily_count + 1:04d}"
    
    def _process_resolution_payment(self, dispute_id: ObjectId, amount: float, 
                                  user_id: ObjectId) -> bool:
        """Process resolution payment (refund, compensation, etc.)."""
        # This would integrate with payment processing systems
        # For now, just log the resolution payment
        try:
            # Add internal message about payment processing
            payment_message = {
                'message': f"Resolution payment of ${amount:.2f} processed",
                'sender_type': 'system',
                'is_internal': True
            }
            self.add_message(dispute_id, payment_message, user_id)
            return True
        except Exception:
            return False