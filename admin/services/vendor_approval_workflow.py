"""
Vendor approval workflow for processing vendor applications
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId

from .base_service import BaseService
from ..models.user import VendorApplication, User, UserRole


class VendorApprovalWorkflow(BaseService):
    """Service for managing vendor application approval workflow."""
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'vendor_applications'
    
    def __init__(self, db, user_manager=None, audit_logger=None):
        super().__init__(db)
        self.user_manager = user_manager
        self.audit_logger = audit_logger
        self.applications_collection = db.vendor_applications
        self.users_collection = db.users
    
    def submit_application(self, user_id: ObjectId, application_data: Dict[str, Any]) -> VendorApplication:
        """Submit a new vendor application."""
        try:
            # Check if user exists
            user = self.user_manager.get_user(user_id) if self.user_manager else None
            if not user:
                raise ValueError("User not found")
            
            # Check if user already has a pending or approved application
            existing = self.applications_collection.find_one({
                'user_id': user_id,
                'status': {'$in': ['pending', 'approved', 'under_review']}
            })
            
            if existing:
                raise ValueError(f"User already has a {existing['status']} vendor application")
            
            # Validate required fields
            required_fields = [
                'business_name', 'business_type', 'business_address',
                'contact_person', 'contact_email', 'contact_phone'
            ]
            
            for field in required_fields:
                if not application_data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            # Create application
            application_data['user_id'] = user_id
            application_data['status'] = 'pending'
            application_data['created_at'] = datetime.utcnow()
            
            application = VendorApplication(**application_data)
            
            # Insert into database
            result = self.applications_collection.insert_one(application.to_dict())
            application.id = result.inserted_id
            
            # Log the action
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=user_id,
                    action='vendor_application_submitted',
                    resource_type='vendor_application',
                    resource_id=str(application.id),
                    details={
                        'business_name': application.business_name,
                        'business_type': application.business_type,
                        'contact_email': application.contact_email
                    }
                )
            
            return application
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=user_id,
                    action='vendor_application_submit_failed',
                    resource_type='vendor_application',
                    resource_id=None,
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def get_application(self, application_id: ObjectId) -> Optional[VendorApplication]:
        """Get vendor application by ID."""
        app_data = self.applications_collection.find_one({'_id': application_id})
        if app_data:
            app_data['id'] = app_data.pop('_id')
            return VendorApplication(**app_data)
        return None
    
    def get_user_application(self, user_id: ObjectId) -> Optional[VendorApplication]:
        """Get the latest vendor application for a user."""
        app_data = self.applications_collection.find_one(
            {'user_id': user_id},
            sort=[('created_at', -1)]
        )
        if app_data:
            app_data['id'] = app_data.pop('_id')
            return VendorApplication(**app_data)
        return None
    
    def list_applications(self, status: Optional[str] = None, limit: int = 50, skip: int = 0) -> List[VendorApplication]:
        """List vendor applications with optional status filter."""
        query = {}
        if status:
            query['status'] = status
        
        cursor = self.applications_collection.find(query).limit(limit).skip(skip).sort('created_at', -1)
        
        applications = []
        for app_data in cursor:
            app_data['id'] = app_data.pop('_id')
            applications.append(VendorApplication(**app_data))
        
        return applications
    
    def count_applications(self, status: Optional[str] = None) -> int:
        """Count vendor applications with optional status filter."""
        query = {}
        if status:
            query['status'] = status
        return self.applications_collection.count_documents(query)
    
    def set_under_review(self, application_id: ObjectId, reviewer_id: ObjectId) -> bool:
        """Set application status to under review."""
        try:
            application = self.get_application(application_id)
            if not application:
                raise ValueError("Application not found")
            
            if application.status != 'pending':
                raise ValueError(f"Cannot review application with status: {application.status}")
            
            # Update application
            application.set_under_review(reviewer_id)
            
            result = self.applications_collection.update_one(
                {'_id': application_id},
                {'$set': application.to_dict()}
            )
            
            if result.modified_count > 0:
                # Log the action
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=reviewer_id,
                        action='vendor_application_under_review',
                        resource_type='vendor_application',
                        resource_id=str(application_id),
                        details={
                            'business_name': application.business_name,
                            'applicant_user_id': str(application.user_id)
                        }
                    )
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=reviewer_id,
                    action='vendor_application_review_failed',
                    resource_type='vendor_application',
                    resource_id=str(application_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def approve_application(self, application_id: ObjectId, reviewer_id: ObjectId, notes: str = '') -> bool:
        """Approve vendor application and upgrade user to vendor role."""
        try:
            application = self.get_application(application_id)
            if not application:
                raise ValueError("Application not found")
            
            if application.status not in ['pending', 'under_review']:
                raise ValueError(f"Cannot approve application with status: {application.status}")
            
            # Approve application
            application.approve(reviewer_id, notes)
            
            # Update application in database
            result = self.applications_collection.update_one(
                {'_id': application_id},
                {'$set': application.to_dict()}
            )
            
            if result.modified_count > 0:
                # Upgrade user to vendor role
                self._upgrade_user_to_vendor(application.user_id, reviewer_id)
                
                # Log the action
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=reviewer_id,
                        action='vendor_application_approved',
                        resource_type='vendor_application',
                        resource_id=str(application_id),
                        details={
                            'business_name': application.business_name,
                            'applicant_user_id': str(application.user_id),
                            'notes': notes
                        }
                    )
                
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=reviewer_id,
                    action='vendor_application_approve_failed',
                    resource_type='vendor_application',
                    resource_id=str(application_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def reject_application(self, application_id: ObjectId, reviewer_id: ObjectId, reason: str, notes: str = '') -> bool:
        """Reject vendor application."""
        try:
            application = self.get_application(application_id)
            if not application:
                raise ValueError("Application not found")
            
            if application.status not in ['pending', 'under_review']:
                raise ValueError(f"Cannot reject application with status: {application.status}")
            
            # Reject application
            application.reject(reviewer_id, reason, notes)
            
            # Update application in database
            result = self.applications_collection.update_one(
                {'_id': application_id},
                {'$set': application.to_dict()}
            )
            
            if result.modified_count > 0:
                # Log the action
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=reviewer_id,
                        action='vendor_application_rejected',
                        resource_type='vendor_application',
                        resource_id=str(application_id),
                        details={
                            'business_name': application.business_name,
                            'applicant_user_id': str(application.user_id),
                            'reason': reason,
                            'notes': notes
                        }
                    )
                
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=reviewer_id,
                    action='vendor_application_reject_failed',
                    resource_type='vendor_application',
                    resource_id=str(application_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def _upgrade_user_to_vendor(self, user_id: ObjectId, upgraded_by: ObjectId) -> None:
        """Upgrade user to vendor role with appropriate permissions."""
        try:
            # Update user role
            updates = {
                'role': UserRole.VENDOR.value,
                'updated_at': datetime.utcnow(),
                'updated_by': upgraded_by
            }
            
            # Get vendor permissions (this would typically come from PermissionEngine)
            vendor_permissions = [
                'product_read', 'product_write',
                'order_read', 'order_write',
                'analytics_read'
            ]
            updates['permissions'] = vendor_permissions
            
            result = self.users_collection.update_one(
                {'_id': user_id},
                {'$set': updates}
            )
            
            if result.modified_count > 0:
                # Log the role upgrade
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=upgraded_by,
                        action='user_role_upgraded',
                        resource_type='user',
                        resource_id=str(user_id),
                        details={
                            'new_role': UserRole.VENDOR.value,
                            'permissions': vendor_permissions,
                            'reason': 'vendor_application_approved'
                        }
                    )
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=upgraded_by,
                    action='user_role_upgrade_failed',
                    resource_type='user',
                    resource_id=str(user_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def update_application(self, application_id: ObjectId, updates: Dict[str, Any], updated_by: Optional[ObjectId] = None) -> bool:
        """Update vendor application details."""
        try:
            # Add timestamp
            updates['updated_at'] = datetime.utcnow()
            if updated_by:
                updates['updated_by'] = updated_by
            
            result = self.applications_collection.update_one(
                {'_id': application_id},
                {'$set': updates}
            )
            
            if result.modified_count > 0:
                # Log the action
                if self.audit_logger:
                    self.audit_logger.log_activity(
                        user_id=updated_by,
                        action='vendor_application_updated',
                        resource_type='vendor_application',
                        resource_id=str(application_id),
                        details={'updated_fields': list(updates.keys())}
                    )
                return True
            
            return False
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_activity(
                    user_id=updated_by,
                    action='vendor_application_update_failed',
                    resource_type='vendor_application',
                    resource_id=str(application_id),
                    details={'error': str(e)},
                    success=False
                )
            raise
    
    def get_application_statistics(self) -> Dict[str, Any]:
        """Get vendor application statistics."""
        pipeline = [
            {
                '$group': {
                    '_id': '$status',
                    'count': {'$sum': 1}
                }
            }
        ]
        
        status_counts = {}
        for result in self.applications_collection.aggregate(pipeline):
            status_counts[result['_id']] = result['count']
        
        # Get recent applications (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = self.applications_collection.count_documents({
            'created_at': {'$gte': thirty_days_ago}
        })
        
        return {
            'total_applications': sum(status_counts.values()),
            'by_status': status_counts,
            'recent_applications_30d': recent_count,
            'pending_review': status_counts.get('pending', 0) + status_counts.get('under_review', 0)
        }
    
    def get_applications_requiring_attention(self) -> List[VendorApplication]:
        """Get applications that require attention (pending or under review for too long)."""
        # Applications pending for more than 7 days or under review for more than 3 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        
        query = {
            '$or': [
                {'status': 'pending', 'created_at': {'$lt': seven_days_ago}},
                {'status': 'under_review', 'reviewed_at': {'$lt': three_days_ago}}
            ]
        }
        
        cursor = self.applications_collection.find(query).sort('created_at', 1)
        
        applications = []
        for app_data in cursor:
            app_data['id'] = app_data.pop('_id')
            applications.append(VendorApplication(**app_data))
        
        return applications