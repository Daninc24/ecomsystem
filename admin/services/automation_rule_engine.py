"""
Automation Rule Engine Service
Handles automated rules for pricing, inventory, and product management
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from bson import ObjectId
import re
from enum import Enum

from .base_service import BaseService
from ..models.product import AutomationRule, RuleConditionType, RuleActionType, ProductStatus


class AutomationRuleEngine(BaseService):
    """Service for managing and executing automation rules."""
    
    def __init__(self, db):
        self.products_collection = db.products
        self.categories_collection = db.product_categories
        self.vendors_collection = db.vendors
        self.analytics_collection = db.analytics_metrics
        super().__init__(db)
    
    def _get_collection_name(self) -> str:
        """Get the MongoDB collection name for this service."""
        return 'automation_rules'
    
    def create_rule(self, rule_data: Dict[str, Any], user_id: ObjectId) -> ObjectId:
        """Create a new automation rule."""
        rule = AutomationRule(**rule_data)
        rule.created_by = user_id
        rule.created_at = datetime.utcnow()
        rule.updated_at = datetime.utcnow()
        
        # Validate rule conditions and actions
        if not self._validate_rule(rule):
            raise ValueError("Invalid rule configuration")
        
        result = self.collection.insert_one(rule.__dict__)
        return result.inserted_id
    
    def update_rule(self, rule_id: ObjectId, updates: Dict[str, Any], user_id: ObjectId) -> bool:
        """Update an existing automation rule."""
        updates['updated_at'] = datetime.utcnow()
        
        # Validate updates if they contain conditions or actions
        if 'conditions' in updates or 'actions' in updates:
            # Get current rule and apply updates for validation
            current_rule = self.collection.find_one({'_id': rule_id})
            if not current_rule:
                return False
            
            temp_rule_data = current_rule.copy()
            temp_rule_data.update(updates)
            temp_rule = AutomationRule(**temp_rule_data)
            
            if not self._validate_rule(temp_rule):
                raise ValueError("Invalid rule configuration")
        
        result = self.collection.update_one(
            {'_id': rule_id},
            {'$set': updates}
        )
        
        return result.modified_count > 0
    
    def delete_rule(self, rule_id: ObjectId) -> bool:
        """Delete an automation rule."""
        result = self.collection.delete_one({'_id': rule_id})
        return result.deleted_count > 0
    
    def get_rule(self, rule_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get a single automation rule."""
        return self.collection.find_one({'_id': rule_id})
    
    def list_rules(self, filters: Dict[str, Any] = None, 
                  page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """List automation rules with filtering and pagination."""
        query = filters or {}
        skip = (page - 1) * limit
        
        rules = list(self.collection.find(query).sort('priority', -1).skip(skip).limit(limit))
        total = self.collection.count_documents(query)
        
        return {
            'rules': rules,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        }
    
    def execute_rules(self, rule_ids: List[ObjectId] = None) -> Dict[str, Any]:
        """Execute automation rules."""
        query = {'is_active': True}
        if rule_ids:
            query['_id'] = {'$in': rule_ids}
        
        rules = list(self.collection.find(query).sort('priority', -1))
        
        execution_results = {
            'total_rules': len(rules),
            'executed_rules': 0,
            'successful_rules': 0,
            'failed_rules': 0,
            'total_products_affected': 0,
            'results': []
        }
        
        for rule in rules:
            try:
                result = self._execute_single_rule(rule)
                execution_results['results'].append(result)
                execution_results['executed_rules'] += 1
                
                if result['success']:
                    execution_results['successful_rules'] += 1
                    execution_results['total_products_affected'] += result['products_affected']
                else:
                    execution_results['failed_rules'] += 1
                
                # Update rule execution statistics
                self._update_rule_stats(rule['_id'], result['success'])
                
            except Exception as e:
                execution_results['results'].append({
                    'rule_id': rule['_id'],
                    'rule_name': rule['name'],
                    'success': False,
                    'error': str(e),
                    'products_affected': 0
                })
                execution_results['executed_rules'] += 1
                execution_results['failed_rules'] += 1
                self._update_rule_stats(rule['_id'], False)
        
        return execution_results
    
    def test_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test a rule without executing actions to see what products would be affected."""
        rule = AutomationRule(**rule_data)
        
        if not self._validate_rule(rule):
            return {'valid': False, 'error': 'Invalid rule configuration'}
        
        # Find matching products
        matching_products = self._find_matching_products(rule.conditions)
        
        return {
            'valid': True,
            'matching_products_count': len(matching_products),
            'matching_products': matching_products[:10],  # Return first 10 for preview
            'estimated_actions': len(rule.actions) * len(matching_products)
        }
    
    def get_rule_execution_history(self, rule_id: ObjectId, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a specific rule."""
        # This would typically be stored in a separate execution log collection
        # For now, we'll return basic stats from the rule document
        rule = self.collection.find_one({'_id': rule_id})
        if not rule:
            return []
        
        return [{
            'rule_id': rule_id,
            'last_executed': rule.get('last_executed'),
            'execution_count': rule.get('execution_count', 0),
            'success_count': rule.get('success_count', 0),
            'failure_count': rule.get('failure_count', 0)
        }]
    
    # Private methods
    
    def _execute_single_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single automation rule."""
        rule_id = rule['_id']
        
        try:
            # Find products matching the rule conditions
            matching_products = self._find_matching_products(rule['conditions'])
            
            if not matching_products:
                return {
                    'rule_id': rule_id,
                    'rule_name': rule['name'],
                    'success': True,
                    'products_affected': 0,
                    'message': 'No products matched the rule conditions'
                }
            
            # Execute actions on matching products
            products_affected = 0
            action_results = []
            
            for action in rule['actions']:
                action_result = self._execute_action(action, matching_products)
                action_results.append(action_result)
                products_affected += action_result.get('products_affected', 0)
            
            return {
                'rule_id': rule_id,
                'rule_name': rule['name'],
                'success': True,
                'products_affected': products_affected,
                'action_results': action_results
            }
            
        except Exception as e:
            return {
                'rule_id': rule_id,
                'rule_name': rule['name'],
                'success': False,
                'error': str(e),
                'products_affected': 0
            }
    
    def _find_matching_products(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find products that match the rule conditions."""
        if not conditions:
            return []
        
        # Build MongoDB query from conditions
        query_parts = []
        
        for condition in conditions:
            condition_type = RuleConditionType(condition['type'])
            query_part = self._build_condition_query(condition_type, condition)
            if query_part:
                query_parts.append(query_part)
        
        if not query_parts:
            return []
        
        # Combine conditions with AND logic
        if len(query_parts) == 1:
            query = query_parts[0]
        else:
            query = {'$and': query_parts}
        
        return list(self.products_collection.find(query))
    
    def _build_condition_query(self, condition_type: RuleConditionType, 
                             condition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build MongoDB query for a specific condition type."""
        
        if condition_type == RuleConditionType.INVENTORY_LEVEL:
            operator = condition.get('operator', 'lt')  # lt, lte, gt, gte, eq
            value = condition.get('value', 0)
            
            mongo_operator = {
                'lt': '$lt',
                'lte': '$lte',
                'gt': '$gt',
                'gte': '$gte',
                'eq': '$eq'
            }.get(operator, '$lt')
            
            return {'inventory.stock': {mongo_operator: value}}
        
        elif condition_type == RuleConditionType.PRICE_RANGE:
            min_price = condition.get('min_price')
            max_price = condition.get('max_price')
            
            price_conditions = {}
            if min_price is not None:
                price_conditions['$gte'] = min_price
            if max_price is not None:
                price_conditions['$lte'] = max_price
            
            return {'pricing.price': price_conditions} if price_conditions else None
        
        elif condition_type == RuleConditionType.CATEGORY:
            category_ids = condition.get('category_ids', [])
            if isinstance(category_ids, str):
                category_ids = [ObjectId(category_ids)]
            elif isinstance(category_ids, list):
                category_ids = [ObjectId(cid) for cid in category_ids]
            
            return {'category_id': {'$in': category_ids}} if category_ids else None
        
        elif condition_type == RuleConditionType.VENDOR:
            vendor_ids = condition.get('vendor_ids', [])
            if isinstance(vendor_ids, str):
                vendor_ids = [ObjectId(vendor_ids)]
            elif isinstance(vendor_ids, list):
                vendor_ids = [ObjectId(vid) for vid in vendor_ids]
            
            return {'vendor_id': {'$in': vendor_ids}} if vendor_ids else None
        
        elif condition_type == RuleConditionType.DATE_RANGE:
            start_date = condition.get('start_date')
            end_date = condition.get('end_date')
            date_field = condition.get('date_field', 'created_at')
            
            date_conditions = {}
            if start_date:
                date_conditions['$gte'] = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
            if end_date:
                date_conditions['$lte'] = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
            
            return {date_field: date_conditions} if date_conditions else None
        
        elif condition_type == RuleConditionType.SALES_VOLUME:
            # This would require analytics data
            operator = condition.get('operator', 'gt')
            value = condition.get('value', 0)
            period_days = condition.get('period_days', 30)
            
            # For now, we'll use a placeholder - in production, this would query analytics
            return {'analytics.sales': {'$gt': value}}
        
        return None
    
    def _execute_action(self, action: Dict[str, Any], products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a specific action on a list of products."""
        action_type = RuleActionType(action['type'])
        products_affected = 0
        
        try:
            if action_type == RuleActionType.UPDATE_PRICE:
                products_affected = self._execute_price_update_action(action, products)
            
            elif action_type == RuleActionType.UPDATE_INVENTORY:
                products_affected = self._execute_inventory_update_action(action, products)
            
            elif action_type == RuleActionType.CHANGE_STATUS:
                products_affected = self._execute_status_change_action(action, products)
            
            elif action_type == RuleActionType.SEND_NOTIFICATION:
                products_affected = self._execute_notification_action(action, products)
            
            elif action_type == RuleActionType.CREATE_PROMOTION:
                products_affected = self._execute_promotion_action(action, products)
            
            return {
                'action_type': action_type.value,
                'success': True,
                'products_affected': products_affected
            }
            
        except Exception as e:
            return {
                'action_type': action_type.value,
                'success': False,
                'error': str(e),
                'products_affected': 0
            }
    
    def _execute_price_update_action(self, action: Dict[str, Any], products: List[Dict[str, Any]]) -> int:
        """Execute price update action."""
        update_type = action.get('update_type', 'percentage')  # percentage, fixed_amount, set_price
        value = action.get('value', 0)
        
        products_affected = 0
        
        for product in products:
            current_price = product.get('pricing', {}).get('price', 0)
            
            if update_type == 'percentage':
                new_price = current_price * (1 + value / 100)
            elif update_type == 'fixed_amount':
                new_price = current_price + value
            elif update_type == 'set_price':
                new_price = value
            else:
                continue
            
            # Ensure price is not negative
            new_price = max(0, new_price)
            
            result = self.products_collection.update_one(
                {'_id': product['_id']},
                {
                    '$set': {
                        'pricing.price': new_price,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                products_affected += 1
        
        return products_affected
    
    def _execute_inventory_update_action(self, action: Dict[str, Any], products: List[Dict[str, Any]]) -> int:
        """Execute inventory update action."""
        update_type = action.get('update_type', 'set')  # set, add, subtract
        quantity = action.get('quantity', 0)
        
        products_affected = 0
        
        for product in products:
            current_stock = product.get('inventory', {}).get('stock', 0)
            
            if update_type == 'set':
                new_stock = quantity
            elif update_type == 'add':
                new_stock = current_stock + quantity
            elif update_type == 'subtract':
                new_stock = max(0, current_stock - quantity)
            else:
                continue
            
            result = self.products_collection.update_one(
                {'_id': product['_id']},
                {
                    '$set': {
                        'inventory.stock': new_stock,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                products_affected += 1
        
        return products_affected
    
    def _execute_status_change_action(self, action: Dict[str, Any], products: List[Dict[str, Any]]) -> int:
        """Execute status change action."""
        new_status = action.get('status', ProductStatus.ACTIVE.value)
        
        if new_status not in [status.value for status in ProductStatus]:
            return 0
        
        product_ids = [product['_id'] for product in products]
        
        result = self.products_collection.update_many(
            {'_id': {'$in': product_ids}},
            {
                '$set': {
                    'status': new_status,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        return result.modified_count
    
    def _execute_notification_action(self, action: Dict[str, Any], products: List[Dict[str, Any]]) -> int:
        """Execute notification action."""
        # This would integrate with a notification system
        # For now, we'll just log the notification
        message = action.get('message', 'Automation rule triggered')
        recipients = action.get('recipients', [])
        
        # In a real implementation, this would send notifications
        # For now, we'll consider all products as "notified"
        return len(products)
    
    def _execute_promotion_action(self, action: Dict[str, Any], products: List[Dict[str, Any]]) -> int:
        """Execute promotion creation action."""
        discount_percentage = action.get('discount_percentage', 10)
        promotion_name = action.get('promotion_name', 'Automated Promotion')
        
        products_affected = 0
        
        for product in products:
            current_price = product.get('pricing', {}).get('price', 0)
            discount_amount = current_price * (discount_percentage / 100)
            sale_price = current_price - discount_amount
            
            result = self.products_collection.update_one(
                {'_id': product['_id']},
                {
                    '$set': {
                        'pricing.sale_price': sale_price,
                        'pricing.discount_percentage': discount_percentage,
                        'promotion.name': promotion_name,
                        'promotion.active': True,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                products_affected += 1
        
        return products_affected
    
    def _validate_rule(self, rule: AutomationRule) -> bool:
        """Validate a rule configuration."""
        # Check that rule has at least one condition and one action
        if not rule.conditions or not rule.actions:
            return False
        
        # Validate each condition
        for condition in rule.conditions:
            if not self._validate_condition(condition):
                return False
        
        # Validate each action
        for action in rule.actions:
            if not self._validate_action(action):
                return False
        
        return True
    
    def _validate_condition(self, condition: Dict[str, Any]) -> bool:
        """Validate a single condition."""
        try:
            condition_type = RuleConditionType(condition['type'])
            
            # Basic validation based on condition type
            if condition_type == RuleConditionType.INVENTORY_LEVEL:
                return 'value' in condition and isinstance(condition['value'], (int, float))
            
            elif condition_type == RuleConditionType.PRICE_RANGE:
                return ('min_price' in condition or 'max_price' in condition)
            
            elif condition_type == RuleConditionType.CATEGORY:
                return 'category_ids' in condition
            
            elif condition_type == RuleConditionType.VENDOR:
                return 'vendor_ids' in condition
            
            elif condition_type == RuleConditionType.DATE_RANGE:
                return ('start_date' in condition or 'end_date' in condition)
            
            elif condition_type == RuleConditionType.SALES_VOLUME:
                return 'value' in condition and isinstance(condition['value'], (int, float))
            
            return True
            
        except (ValueError, KeyError):
            return False
    
    def _validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate a single action."""
        try:
            action_type = RuleActionType(action['type'])
            
            # Basic validation based on action type
            if action_type == RuleActionType.UPDATE_PRICE:
                return 'value' in action and isinstance(action['value'], (int, float))
            
            elif action_type == RuleActionType.UPDATE_INVENTORY:
                return 'quantity' in action and isinstance(action['quantity'], int)
            
            elif action_type == RuleActionType.CHANGE_STATUS:
                return 'status' in action
            
            elif action_type == RuleActionType.SEND_NOTIFICATION:
                return 'message' in action
            
            elif action_type == RuleActionType.CREATE_PROMOTION:
                return 'discount_percentage' in action
            
            return True
            
        except (ValueError, KeyError):
            return False
    
    def _update_rule_stats(self, rule_id: ObjectId, success: bool):
        """Update rule execution statistics."""
        update_data = {
            'last_executed': datetime.utcnow(),
            '$inc': {
                'execution_count': 1,
                'success_count' if success else 'failure_count': 1
            }
        }
        
        self.collection.update_one(
            {'_id': rule_id},
            update_data
        )