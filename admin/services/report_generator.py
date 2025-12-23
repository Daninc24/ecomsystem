"""
Report generation service for financial and operational analytics
"""

import csv
import json
from datetime import datetime, timedelta
from io import StringIO
from typing import Any, Dict, List, Optional
from bson import ObjectId

from ..models.order import FinancialReport, OrderStatus, PaymentStatus, RefundStatus
from .base_service import BaseService


class ReportGenerator(BaseService):
    """Service for generating financial and operational reports."""
    
    def __init__(self, db_client):
        super().__init__(db_client)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'financial_reports'
    
    def generate_sales_report(self, start_date: datetime, end_date: datetime, 
                            filters: Dict[str, Any] = None, user_id: ObjectId = None) -> FinancialReport:
        """Generate comprehensive sales report."""
        # Build query filter
        query_filter = {
            'created_at': {'$gte': start_date, '$lte': end_date},
            'status': {'$ne': OrderStatus.CANCELLED.value}
        }
        
        if filters:
            if 'vendor_id' in filters:
                query_filter['vendor_id'] = ObjectId(filters['vendor_id'])
            if 'customer_id' in filters:
                query_filter['customer_id'] = ObjectId(filters['customer_id'])
            if 'payment_status' in filters:
                query_filter['payment_status'] = filters['payment_status']
        
        # Aggregate sales data
        pipeline = [
            {'$match': query_filter},
            {'$group': {
                '_id': None,
                'total_orders': {'$sum': 1},
                'total_revenue': {'$sum': '$total_amount'},
                'total_taxes': {'$sum': '$tax_amount'},
                'total_shipping': {'$sum': '$shipping_amount'},
                'total_discounts': {'$sum': '$discount_amount'},
                'orders_by_status': {
                    '$push': {
                        'status': '$status',
                        'amount': '$total_amount'
                    }
                },
                'revenue_by_vendor': {
                    '$push': {
                        'vendor_id': '$vendor_id',
                        'amount': '$total_amount'
                    }
                }
            }}
        ]
        
        result = list(self.db.orders.aggregate(pipeline))
        
        if not result:
            sales_data = {
                'total_orders': 0,
                'total_revenue': 0.0,
                'total_taxes': 0.0,
                'total_shipping': 0.0,
                'total_discounts': 0.0,
                'orders_by_status': {},
                'revenue_by_vendor': {}
            }
        else:
            sales_data = result[0]
            
            # Process orders by status
            status_counts = {}
            for order in sales_data.get('orders_by_status', []):
                status = order['status']
                if status not in status_counts:
                    status_counts[status] = 0
                status_counts[status] += 1
            sales_data['orders_by_status'] = status_counts
            
            # Process revenue by vendor
            vendor_revenue = {}
            for order in sales_data.get('revenue_by_vendor', []):
                vendor_id = str(order.get('vendor_id', 'direct'))
                if vendor_id not in vendor_revenue:
                    vendor_revenue[vendor_id] = 0.0
                vendor_revenue[vendor_id] += order['amount']
            sales_data['revenue_by_vendor'] = vendor_revenue
        
        # Get refund data
        refund_data = self._get_refund_data(start_date, end_date, filters)
        
        # Create report
        report = FinancialReport(
            report_name=f"Sales Report {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            report_type='sales',
            period_start=start_date,
            period_end=end_date,
            total_orders=sales_data.get('total_orders', 0),
            total_revenue=sales_data.get('total_revenue', 0.0),
            total_refunds=refund_data.get('total_refunds', 0.0),
            total_taxes=sales_data.get('total_taxes', 0.0),
            total_shipping=sales_data.get('total_shipping', 0.0),
            net_revenue=sales_data.get('total_revenue', 0.0) - refund_data.get('total_refunds', 0.0),
            orders_by_status=sales_data.get('orders_by_status', {}),
            revenue_by_vendor=sales_data.get('revenue_by_vendor', {}),
            generated_by=user_id
        )
        
        # Save report
        result = self.db.financial_reports.insert_one(report.to_dict())
        report.id = result.inserted_id
        
        return report
    
    def generate_refund_report(self, start_date: datetime, end_date: datetime,
                             filters: Dict[str, Any] = None, user_id: ObjectId = None) -> FinancialReport:
        """Generate refund analysis report."""
        # Build query filter
        query_filter = {
            'created_at': {'$gte': start_date, '$lte': end_date}
        }
        
        if filters:
            if 'status' in filters:
                query_filter['status'] = filters['status']
            if 'refund_type' in filters:
                query_filter['refund_type'] = filters['refund_type']
        
        # Aggregate refund data
        pipeline = [
            {'$match': query_filter},
            {'$group': {
                '_id': None,
                'total_refunds': {'$sum': 1},
                'total_refund_amount': {'$sum': '$refund_amount'},
                'refunds_by_status': {
                    '$push': {
                        'status': '$status',
                        'amount': '$refund_amount'
                    }
                },
                'refunds_by_reason': {
                    '$push': '$refund_reason'
                }
            }}
        ]
        
        result = list(self.db.refunds.aggregate(pipeline))
        
        if not result:
            refund_data = {
                'total_refunds': 0,
                'total_refund_amount': 0.0,
                'refunds_by_status': {},
                'refunds_by_reason': {}
            }
        else:
            refund_data = result[0]
            
            # Process refunds by status
            status_counts = {}
            for refund in refund_data.get('refunds_by_status', []):
                status = refund['status']
                if status not in status_counts:
                    status_counts[status] = {'count': 0, 'amount': 0.0}
                status_counts[status]['count'] += 1
                status_counts[status]['amount'] += refund['amount']
            refund_data['refunds_by_status'] = status_counts
            
            # Process refunds by reason
            reason_counts = {}
            for reason in refund_data.get('refunds_by_reason', []):
                if reason:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
            refund_data['refunds_by_reason'] = reason_counts
        
        # Create report
        report = FinancialReport(
            report_name=f"Refund Report {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            report_type='refunds',
            period_start=start_date,
            period_end=end_date,
            total_orders=refund_data.get('total_refunds', 0),
            total_refunds=refund_data.get('total_refund_amount', 0.0),
            orders_by_status=refund_data.get('refunds_by_status', {}),
            generated_by=user_id
        )
        
        # Save report
        result = self.db.financial_reports.insert_one(report.to_dict())
        report.id = result.inserted_id
        
        return report
    
    def generate_operational_report(self, start_date: datetime, end_date: datetime,
                                  user_id: ObjectId = None) -> Dict[str, Any]:
        """Generate operational metrics report."""
        # Order processing metrics
        order_metrics = self._get_order_processing_metrics(start_date, end_date)
        
        # Shipping metrics
        shipping_metrics = self._get_shipping_metrics(start_date, end_date)
        
        # Customer service metrics
        dispute_metrics = self._get_dispute_metrics(start_date, end_date)
        
        # Inventory metrics
        inventory_metrics = self._get_inventory_metrics(start_date, end_date)
        
        return {
            'report_name': f"Operational Report {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'period_start': start_date,
            'period_end': end_date,
            'order_processing': order_metrics,
            'shipping': shipping_metrics,
            'customer_service': dispute_metrics,
            'inventory': inventory_metrics,
            'generated_at': datetime.utcnow(),
            'generated_by': user_id
        }
    
    def export_report(self, report_id: ObjectId, export_format: str = 'json') -> Dict[str, Any]:
        """Export report in specified format."""
        report_data = self.db.financial_reports.find_one({'_id': report_id})
        if not report_data:
            return {'success': False, 'error': 'Report not found'}
        
        report = FinancialReport.from_dict(report_data)
        
        try:
            if export_format.lower() == 'csv':
                csv_data = self._export_to_csv(report)
                return {
                    'success': True,
                    'format': 'csv',
                    'data': csv_data,
                    'filename': f"{report.report_name.replace(' ', '_')}.csv"
                }
            elif export_format.lower() == 'json':
                json_data = self._export_to_json(report)
                return {
                    'success': True,
                    'format': 'json',
                    'data': json_data,
                    'filename': f"{report.report_name.replace(' ', '_')}.json"
                }
            else:
                return {'success': False, 'error': f'Unsupported format: {export_format}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_report(self, report_id: ObjectId) -> Optional[FinancialReport]:
        """Get report by ID."""
        report_data = self.db.financial_reports.find_one({'_id': report_id})
        if report_data:
            return FinancialReport.from_dict(report_data)
        return None
    
    def get_reports_by_type(self, report_type: str, limit: int = 50) -> List[FinancialReport]:
        """Get reports by type."""
        reports_data = self.db.financial_reports.find({'report_type': report_type}).limit(limit)
        return [FinancialReport.from_dict(report_data) for report_data in reports_data]
    
    def get_recent_reports(self, limit: int = 20) -> List[FinancialReport]:
        """Get recent reports."""
        reports_data = self.db.financial_reports.find().sort('created_at', -1).limit(limit)
        return [FinancialReport.from_dict(report_data) for report_data in reports_data]
    
    def _get_refund_data(self, start_date: datetime, end_date: datetime, 
                        filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get refund data for the specified period."""
        query_filter = {
            'created_at': {'$gte': start_date, '$lte': end_date},
            'status': RefundStatus.COMPLETED.value
        }
        
        if filters and 'vendor_id' in filters:
            # Get orders for this vendor and match refunds
            vendor_orders = list(self.db.orders.find(
                {'vendor_id': ObjectId(filters['vendor_id'])},
                {'_id': 1}
            ))
            order_ids = [order['_id'] for order in vendor_orders]
            query_filter['order_id'] = {'$in': order_ids}
        
        pipeline = [
            {'$match': query_filter},
            {'$group': {
                '_id': None,
                'total_refunds': {'$sum': '$refund_amount'}
            }}
        ]
        
        result = list(self.db.refunds.aggregate(pipeline))
        return {'total_refunds': result[0]['total_refunds'] if result else 0.0}
    
    def _get_order_processing_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get order processing metrics."""
        pipeline = [
            {'$match': {'created_at': {'$gte': start_date, '$lte': end_date}}},
            {'$group': {
                '_id': None,
                'total_orders': {'$sum': 1},
                'avg_processing_time': {
                    '$avg': {'$subtract': ['$shipped_date', '$created_at']}
                },
                'orders_by_status': {'$push': '$status'}
            }}
        ]
        
        result = list(self.db.orders.aggregate(pipeline))
        
        if not result:
            return {'total_orders': 0, 'avg_processing_time_hours': 0, 'fulfillment_rate': 0}
        
        data = result[0]
        
        # Calculate fulfillment rate
        statuses = data.get('orders_by_status', [])
        fulfilled_count = sum(1 for status in statuses if status in ['shipped', 'delivered'])
        fulfillment_rate = (fulfilled_count / len(statuses)) * 100 if statuses else 0
        
        # Convert processing time to hours
        avg_processing_ms = data.get('avg_processing_time', 0) or 0
        avg_processing_hours = avg_processing_ms / (1000 * 60 * 60) if avg_processing_ms else 0
        
        return {
            'total_orders': data.get('total_orders', 0),
            'avg_processing_time_hours': round(avg_processing_hours, 2),
            'fulfillment_rate': round(fulfillment_rate, 2)
        }
    
    def _get_shipping_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get shipping performance metrics."""
        pipeline = [
            {'$match': {
                'shipped_date': {'$gte': start_date, '$lte': end_date},
                'shipping_status': {'$exists': True}
            }},
            {'$group': {
                '_id': None,
                'total_shipments': {'$sum': 1},
                'avg_delivery_time': {
                    '$avg': {'$subtract': ['$delivered_date', '$shipped_date']}
                },
                'delivery_success_rate': {
                    '$avg': {
                        '$cond': [
                            {'$eq': ['$shipping_status', 'delivered']},
                            1, 0
                        ]
                    }
                }
            }}
        ]
        
        result = list(self.db.orders.aggregate(pipeline))
        
        if not result:
            return {'total_shipments': 0, 'avg_delivery_time_days': 0, 'delivery_success_rate': 0}
        
        data = result[0]
        
        # Convert delivery time to days
        avg_delivery_ms = data.get('avg_delivery_time', 0) or 0
        avg_delivery_days = avg_delivery_ms / (1000 * 60 * 60 * 24) if avg_delivery_ms else 0
        
        return {
            'total_shipments': data.get('total_shipments', 0),
            'avg_delivery_time_days': round(avg_delivery_days, 2),
            'delivery_success_rate': round((data.get('delivery_success_rate', 0) or 0) * 100, 2)
        }
    
    def _get_dispute_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get customer service dispute metrics."""
        pipeline = [
            {'$match': {'created_at': {'$gte': start_date, '$lte': end_date}}},
            {'$group': {
                '_id': None,
                'total_disputes': {'$sum': 1},
                'avg_resolution_time': {
                    '$avg': {'$subtract': ['$resolved_date', '$created_at']}
                },
                'resolution_rate': {
                    '$avg': {
                        '$cond': [
                            {'$eq': ['$status', 'resolved']},
                            1, 0
                        ]
                    }
                }
            }}
        ]
        
        result = list(self.db.disputes.aggregate(pipeline))
        
        if not result:
            return {'total_disputes': 0, 'avg_resolution_time_hours': 0, 'resolution_rate': 0}
        
        data = result[0]
        
        # Convert resolution time to hours
        avg_resolution_ms = data.get('avg_resolution_time', 0) or 0
        avg_resolution_hours = avg_resolution_ms / (1000 * 60 * 60) if avg_resolution_ms else 0
        
        return {
            'total_disputes': data.get('total_disputes', 0),
            'avg_resolution_time_hours': round(avg_resolution_hours, 2),
            'resolution_rate': round((data.get('resolution_rate', 0) or 0) * 100, 2)
        }
    
    def _get_inventory_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get inventory performance metrics."""
        # This would typically analyze inventory transactions
        # For now, return basic metrics
        return {
            'low_stock_items': 0,
            'out_of_stock_items': 0,
            'inventory_turnover': 0.0
        }
    
    def _export_to_csv(self, report: FinancialReport) -> str:
        """Export report to CSV format."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Report Name', report.report_name])
        writer.writerow(['Report Type', report.report_type])
        writer.writerow(['Period', f"{report.period_start} to {report.period_end}"])
        writer.writerow([])
        
        # Write summary data
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Orders', report.total_orders])
        writer.writerow(['Total Revenue', f"${report.total_revenue:.2f}"])
        writer.writerow(['Total Refunds', f"${report.total_refunds:.2f}"])
        writer.writerow(['Net Revenue', f"${report.net_revenue:.2f}"])
        writer.writerow([])
        
        # Write orders by status
        if report.orders_by_status:
            writer.writerow(['Orders by Status'])
            writer.writerow(['Status', 'Count'])
            for status, count in report.orders_by_status.items():
                writer.writerow([status, count])
        
        return output.getvalue()
    
    def _export_to_json(self, report: FinancialReport) -> str:
        """Export report to JSON format."""
        report_dict = report.to_dict()
        
        # Convert ObjectId and datetime objects to strings
        def convert_objects(obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_objects(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_objects(item) for item in obj]
            return obj
        
        converted_dict = convert_objects(report_dict)
        return json.dumps(converted_dict, indent=2)