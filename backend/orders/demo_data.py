"""
Demo data for testing when no real orders are available
"""
from datetime import datetime, timedelta

def get_demo_ready_to_dispatch():
    """Get demo Ready To Dispatch orders"""
    return {
        'count': 3,
        'orders': [
            {
                'awb': 'DEMO1369010468790',
                'status': 'Manifested',
                'customer_name': 'Rajesh Kumar',
                'customer_mobile': '+91 9876543210',
                'customer_address': '123, MG Road, Bangalore',
                'customer_pincode': '560001',
                'order_date': datetime.now().strftime('%Y-%m-%d'),
                'weight': '0.5',
                'cod_amount': '1500',
                'last_scan': {
                    'scan_location': 'Bangalore Hub',
                    'scan_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'remarks': 'Package ready for dispatch'
                }
            },
            {
                'awb': 'DEMO1369010468791',
                'status': 'Not Picked',
                'customer_name': 'Priya Sharma',
                'customer_mobile': '+91 9123456789',
                'customer_address': '456, Park Street, Delhi',
                'customer_pincode': '110001',
                'order_date': datetime.now().strftime('%Y-%m-%d'),
                'weight': '1.2',
                'cod_amount': '2500',
                'last_scan': {
                    'scan_location': 'Delhi Hub',
                    'scan_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'remarks': 'Awaiting pickup'
                }
            },
            {
                'awb': 'DEMO1369010468792',
                'status': 'Manifested',
                'customer_name': 'Amit Patel',
                'customer_mobile': '+91 9988776655',
                'customer_address': '789, CG Road, Ahmedabad',
                'customer_pincode': '380001',
                'order_date': datetime.now().strftime('%Y-%m-%d'),
                'weight': '0.8',
                'cod_amount': '1800',
                'last_scan': {
                    'scan_location': 'Ahmedabad Hub',
                    'scan_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'remarks': 'Ready to ship'
                }
            }
        ]
    }


def get_demo_in_transit():
    """Get demo In Transit orders with some delayed"""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    return {
        'count': 4,
        'delayed_count': 2,
        'orders': [
            {
                'awb': 'DEMO1369010468793',
                'status': 'In Transit',
                'customer_name': 'Sneha Reddy',
                'customer_mobile': '+91 9876512345',
                'customer_address': '321, Jubilee Hills, Hyderabad',
                'customer_pincode': '500033',
                'order_date': (today - timedelta(days=2)).strftime('%Y-%m-%d'),
                'estimated_delivery_date': yesterday.strftime('%Y-%m-%d'),
                'is_delayed': True,
                'weight': '1.5',
                'cod_amount': '3200',
                'last_scan': {
                    'scan_location': 'Hyderabad Hub',
                    'scan_datetime': today.strftime('%Y-%m-%d %H:%M:%S'),
                    'remarks': 'Out for delivery'
                },
                'scan_history': [
                    {
                        'scan_location': 'Mumbai Hub',
                        'scan_datetime': (today - timedelta(days=2)).strftime('%Y-%m-%d 10:30:00'),
                        'remarks': 'Picked up'
                    },
                    {
                        'scan_location': 'Pune Hub',
                        'scan_datetime': (today - timedelta(days=1)).strftime('%Y-%m-%d 14:20:00'),
                        'remarks': 'In transit'
                    },
                    {
                        'scan_location': 'Hyderabad Hub',
                        'scan_datetime': today.strftime('%Y-%m-%d 09:15:00'),
                        'remarks': 'Out for delivery'
                    }
                ]
            },
            {
                'awb': 'DEMO1369010468794',
                'status': 'Out For Delivery',
                'customer_name': 'Vikram Singh',
                'customer_mobile': '+91 9123498765',
                'customer_address': '654, Sector 18, Noida',
                'customer_pincode': '201301',
                'order_date': (today - timedelta(days=1)).strftime('%Y-%m-%d'),
                'estimated_delivery_date': tomorrow.strftime('%Y-%m-%d'),
                'is_delayed': False,
                'weight': '0.6',
                'cod_amount': '1200',
                'last_scan': {
                    'scan_location': 'Noida Hub',
                    'scan_datetime': today.strftime('%Y-%m-%d %H:%M:%S'),
                    'remarks': 'Out for delivery'
                },
                'scan_history': [
                    {
                        'scan_location': 'Delhi Hub',
                        'scan_datetime': (today - timedelta(days=1)).strftime('%Y-%m-%d 11:00:00'),
                        'remarks': 'Picked up'
                    },
                    {
                        'scan_location': 'Noida Hub',
                        'scan_datetime': today.strftime('%Y-%m-%d 08:30:00'),
                        'remarks': 'Out for delivery'
                    }
                ]
            },
            {
                'awb': 'DEMO1369010468795',
                'status': 'Reached At Destination',
                'customer_name': 'Anita Desai',
                'customer_mobile': '+91 9876567890',
                'customer_address': '987, Marine Drive, Mumbai',
                'customer_pincode': '400002',
                'order_date': (today - timedelta(days=3)).strftime('%Y-%m-%d'),
                'estimated_delivery_date': (today - timedelta(days=1)).strftime('%Y-%m-%d'),
                'is_delayed': True,
                'weight': '2.0',
                'cod_amount': '4500',
                'last_scan': {
                    'scan_location': 'Mumbai Hub',
                    'scan_datetime': today.strftime('%Y-%m-%d %H:%M:%S'),
                    'remarks': 'Reached destination hub'
                },
                'scan_history': [
                    {
                        'scan_location': 'Bangalore Hub',
                        'scan_datetime': (today - timedelta(days=3)).strftime('%Y-%m-%d 09:00:00'),
                        'remarks': 'Picked up'
                    },
                    {
                        'scan_location': 'Pune Hub',
                        'scan_datetime': (today - timedelta(days=2)).strftime('%Y-%m-%d 13:45:00'),
                        'remarks': 'In transit'
                    },
                    {
                        'scan_location': 'Mumbai Hub',
                        'scan_datetime': today.strftime('%Y-%m-%d 07:20:00'),
                        'remarks': 'Reached destination'
                    }
                ]
            },
            {
                'awb': 'DEMO1369010468796',
                'status': 'Picked Up',
                'customer_name': 'Rahul Joshi',
                'customer_mobile': '+91 9988112233',
                'customer_address': '147, Lake Road, Kolkata',
                'customer_pincode': '700029',
                'order_date': today.strftime('%Y-%m-%d'),
                'estimated_delivery_date': (today + timedelta(days=2)).strftime('%Y-%m-%d'),
                'is_delayed': False,
                'weight': '0.9',
                'cod_amount': '2100',
                'last_scan': {
                    'scan_location': 'Kolkata Hub',
                    'scan_datetime': today.strftime('%Y-%m-%d %H:%M:%S'),
                    'remarks': 'Picked up from seller'
                },
                'scan_history': [
                    {
                        'scan_location': 'Kolkata Hub',
                        'scan_datetime': today.strftime('%Y-%m-%d 10:00:00'),
                        'remarks': 'Picked up'
                    }
                ]
            }
        ]
    }
