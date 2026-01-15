#!/usr/bin/env python3

from flask import Flask, render_template, request
import psycopg2
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# Helper function to generate category colors (for templates)
def get_category_color(category):
    """Generate consistent color for categories"""
    colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', 
        '#FF9F40', '#8AC27A', '#E763B5', '#FFC107', '#663399'
    ]
    
    # Simple hash function to get consistent color
    hash_value = 0
    for char in category:
        hash_value = ord(char) + ((hash_value << 5) - hash_value)
    
    index = abs(hash_value) % len(colors)
    return colors[index]

# Register the function as a template global
app.jinja_env.globals['get_category_color'] = get_category_color

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    return conn

def get_monthly_yearly_balances():
    """Get monthly and yearly balance information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get monthly balances (positive = income, negative = expenses)
        monthly_query = """
            SELECT 
                EXTRACT(YEAR FROM transaction_date) as year,
                EXTRACT(MONTH FROM transaction_date) as month,
                SUM(amount) as total_amount,
                CASE 
                    WHEN SUM(amount) > 0 THEN 'positive'
                    WHEN SUM(amount) < 0 THEN 'negative'
                    ELSE 'zero'
                END as balance_status
            FROM processed_records 
            GROUP BY EXTRACT(YEAR FROM transaction_date), EXTRACT(MONTH FROM transaction_date)
            ORDER BY year DESC, month DESC
        """
        
        cursor.execute(monthly_query)
        monthly_balances = cursor.fetchall()
        
        # Get yearly balances
        yearly_query = """
            SELECT 
                EXTRACT(YEAR FROM transaction_date) as year,
                SUM(amount) as total_amount,
                CASE 
                    WHEN SUM(amount) > 0 THEN 'positive'
                    WHEN SUM(amount) < 0 THEN 'negative'
                    ELSE 'zero'
                END as balance_status
            FROM processed_records 
            GROUP BY EXTRACT(YEAR FROM transaction_date)
            ORDER BY year DESC
        """
        
        cursor.execute(yearly_query)
        yearly_balances = cursor.fetchall()
        
        # Format monthly data
        formatted_monthly = []
        for record in monthly_balances:
            year = int(record[0])
            month = int(record[1])
            amount = float(record[2]) if record[2] is not None else 0.0
            status = record[3]
            
            # Format month name
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            month_name = month_names[month - 1] if 1 <= month <= 12 else 'Unknown'
            
            formatted_monthly.append({
                'year': year,
                'month': month,
                'month_name': month_name,
                'amount': amount,
                'status': status
            })
        
        # Format yearly data
        formatted_yearly = []
        for record in yearly_balances:
            year = int(record[0])
            amount = float(record[1]) if record[1] is not None else 0.0
            status = record[2]
            
            formatted_yearly.append({
                'year': year,
                'amount': amount,
                'status': status
            })
        
        cursor.close()
        conn.close()
        
        return formatted_monthly, formatted_yearly
        
    except Exception as e:
        logging.error(f"Error fetching monthly/yearly balances: {str(e)}")
        logging.debug("Traceback:")
        import traceback
        traceback.print_exc()
        return [], []

def get_spending_data(time_period, category_filter=None, start_date=None, end_date=None):
    """Get spending data by category for specified time period or date range"""
    
    # Debug: Log what we're trying to do
    logging.info(f"Fetching spending data for time period: {time_period}")
    logging.info(f"Category filter: {category_filter}")
    logging.info(f"Start date: {start_date}, End date: {end_date}")
    
    # Build the date filter - prioritize custom date range
    if start_date and end_date:
        # Custom date range provided
        date_filter = "transaction_date >= %s AND transaction_date <= %s"
        params = (start_date, end_date)
    else:
        # Use the standard time period logic
        if time_period == 'day':
            date_filter = "DATE(transaction_date) = CURRENT_DATE"
            params = ()
        elif time_period == 'week':
            date_filter = "EXTRACT(YEAR FROM transaction_date) = EXTRACT(YEAR FROM CURRENT_DATE) AND EXTRACT(WEEK FROM transaction_date) = EXTRACT(WEEK FROM CURRENT_DATE)"
            params = ()
        elif time_period == 'month':
            date_filter = "EXTRACT(YEAR FROM transaction_date) = EXTRACT(YEAR FROM CURRENT_DATE) AND EXTRACT(MONTH FROM transaction_date) = EXTRACT(MONTH FROM CURRENT_DATE)"
            params = ()
        elif time_period == 'year':
            date_filter = "EXTRACT(YEAR FROM transaction_date) = EXTRACT(YEAR FROM CURRENT_DATE)"
            params = ()
        else:
            date_filter = "1=1"  # All records if no filter
            params = ()
    
    # Build query with optional category filter
    if category_filter:
        where_clause = f"WHERE {date_filter} AND category = %s"
        params = params + (category_filter,)
    else:
        where_clause = f"WHERE {date_filter}"
    
    query = """
        SELECT 
            COALESCE(category, 'Uncategorized') as category,
            SUM(amount) as total_amount
        FROM processed_records 
        """ + where_clause + """
        GROUP BY category
        ORDER BY total_amount DESC
    """
    
    # Log the actual query being executed
    logging.debug(f"Executing SQL Query: {query}")
    logging.debug(f"Query Parameters: {params}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        # Debug: Check how many rows are returned
        records = cursor.fetchall()
        logging.debug(f"Query returned {len(records)} records")
        
        # Format the results
        spending_data = []
        total_spending = 0
        
        for record in records:
            try:
                category = str(record[0]) if record[0] is not None else 'Uncategorized'
                amount = float(record[1]) if record[1] is not None else 0.0
                spending_data.append({
                    'category': category,
                    'amount': amount
                })
                total_spending += amount
            except Exception as e:
                logging.error(f"Error processing record {record}: {str(e)}")
                continue
            
        logging.info(f"Total spending calculated: {total_spending}")
        logging.info(f"Spending data items: {len(spending_data)}")
        
        cursor.close()
        conn.close()
        
        return spending_data, total_spending
        
    except Exception as e:
        logging.error(f"Error fetching spending data: {str(e)}")
        logging.debug("Traceback:")
        import traceback
        traceback.print_exc()
        return [], 0

@app.route('/')
def index():
    # Get filter parameters
    time_period = request.args.get('time_period', 'month')
    category_filter = request.args.get('category', None)
    
    # Handle custom date ranges
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Get spending data for the specified period
    spending_data, total_spending = get_spending_data(time_period, category_filter, start_date, end_date)
    
    # Get monthly and yearly balances
    monthly_balances, yearly_balances = get_monthly_yearly_balances()
    
    # Pagination for balances - default to 10 items per page
    monthly_page = request.args.get('monthly_page', 1, type=int)
    yearly_page = request.args.get('yearly_page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Validate pagination parameters
    if monthly_page < 1:
        monthly_page = 1
    if yearly_page < 1:
        yearly_page = 1
    if per_page < 1 or per_page > 100:
        per_page = 10
    
    # Calculate offsets for pagination
    monthly_offset = (monthly_page - 1) * per_page
    yearly_offset = (yearly_page - 1) * per_page
    
    # Paginate monthly balances
    paginated_monthly = monthly_balances[monthly_offset:monthly_offset + per_page]
    monthly_total_pages = (len(monthly_balances) + per_page - 1) // per_page
    
    # Paginate yearly balances
    paginated_yearly = yearly_balances[yearly_offset:yearly_offset + per_page]
    yearly_total_pages = (len(yearly_balances) + per_page - 1) // per_page
    
    return render_template('index.html', 
                         spending_data=spending_data,
                         total_spending=total_spending,
                         time_period=time_period,
                         category_filter=category_filter,
                         start_date=start_date,
                         end_date=end_date,
                         monthly_balances=paginated_monthly,
                         yearly_balances=paginated_yearly,
                         monthly_total_pages=monthly_total_pages,
                         yearly_total_pages=yearly_total_pages,
                         monthly_page=monthly_page,
                         yearly_page=yearly_page,
                         per_page=per_page)

@app.route('/admin')
def admin():
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Validate pagination parameters
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 10
    
    # Calculate offset for SQL query
    offset = (page - 1) * per_page
    
    try:
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query to get unprocessed financial records using your actual table structure
        query = """
            SELECT id, record_id_bank, transaction_date, currency_date, account, description, amount, currency
            FROM unprocessed_records 
            ORDER BY transaction_date DESC
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, (per_page, offset))
        records = cursor.fetchall()
        
        # Get total count for pagination
        count_query = "SELECT COUNT(*) FROM unprocessed_records"
        cursor.execute(count_query)
        total_count = cursor.fetchone()[0]
        
        # Calculate total pages
        total_pages = (total_count + per_page - 1) // per_page
        
        # Close connections
        cursor.close()
        conn.close()
        
        return render_template('admin.html', 
                             records=records,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             total_count=total_count)
                             
    except Exception as e:
        logging.error(f"Error in admin route: {str(e)}")
        logging.debug("Traceback:")
        import traceback
        traceback.print_exc()
        return f"Error fetching records: {str(e)}", 500

@app.route('/record_transformer')
def record_transformer():
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get filter parameters
    category_filter = request.args.get('category', None)
    search_description = request.args.get('search', None)
    
    # Get sorting parameters
    sort_by = request.args.get('sort_by', 'transaction_date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Validate pagination parameters
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 10
    
    # Validate sort parameters
    valid_sort_fields = ['record_id_bank', 'transaction_date', 'currency_date', 'account', 'description', 'amount', 'currency', 'category']
    if sort_by not in valid_sort_fields:
        sort_by = 'transaction_date'
    
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
    
    # Calculate offset for SQL query
    offset = (page - 1) * per_page
    
    try:
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query to get processed financial records with filtering
        # We need to get categories first for the filter dropdown
        category_query = "SELECT DISTINCT category FROM processed_records WHERE category IS NOT NULL ORDER BY category"
        cursor.execute(category_query)
        categories = [row[0] for row in cursor.fetchall()]
        
        # Main query to get records
        base_query = """
            SELECT record_id_bank, transaction_date, currency_date, account, description, amount, currency, category
            FROM processed_records 
        """
        
        params = []
        where_clauses = []
        
        # Add category filter if specified
        if category_filter:
            where_clauses.append("category = %s")
            params.append(category_filter)
            
        # Add search filter if specified
        if search_description:
            where_clauses.append("description ILIKE %s")
            params.append(f"%{search_description}%")
        
        # Build the complete query
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
            
        # Add sorting
        base_query += " ORDER BY " + sort_by + " " + sort_order + " LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        cursor.execute(base_query, params)
        records = cursor.fetchall()
        
        # Get total count for pagination
        count_query = "SELECT COUNT(*) FROM processed_records"
        
        # Rebuild the WHERE clause for counting
        if where_clauses:
            count_query += " WHERE " + " AND ".join(where_clauses)
            
        cursor.execute(count_query, params[:-2] if where_clauses else ())
        total_count = cursor.fetchone()[0]
        
        # Calculate total pages
        total_pages = (total_count + per_page - 1) // per_page
        
        # Close connections
        cursor.close()
        conn.close()
        
        # Debug: Print records to see what we're getting
        logging.debug(f"Fetched {len(records)} records from database")
        if records:
            logging.debug(f"First record structure: {records[0]}")
        
        return render_template('record_transformer.html', 
                             records=records,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             total_count=total_count,
                             categories=categories,
                             category_filter=category_filter,
                             search_description=search_description,
                             sort_by=sort_by,
                             sort_order=sort_order)
                             
    except Exception as e:
        logging.error(f"Error in record_transformer: {str(e)}")
        logging.debug("Traceback:")
        import traceback
        traceback.print_exc()
        return f"Error fetching records: {str(e)}", 500

@app.route('/update_categories', methods=['POST'])
def update_categories():
    try:
        # Get form data
        record_ids_str = request.form.get('record_ids')
        new_category = request.form.get('new_category')
        
        if not record_ids_str or not new_category:
            return "Missing record IDs or category", 400
            
        # Parse comma-separated record IDs
        record_ids = [id.strip() for id in record_ids_str.split(',') if id.strip()]
        
        if not record_ids:
            return "No valid record IDs provided", 400
            
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update records with new category
        update_query = """
            UPDATE processed_records 
            SET category = %s 
            WHERE record_id_bank = ANY(%s)
        """
        cursor.execute(update_query, (new_category, record_ids))
        
        # Commit the changes
        conn.commit()
        
        # Close connections
        cursor.close()
        conn.close()
        
        return f"Successfully updated {len(record_ids)} records to category '{new_category}'", 200
        
    except Exception as e:
        logging.error(f"Error updating categories: {str(e)}")
        logging.debug("Traceback:")
        import traceback
        traceback.print_exc()
        return f"Error updating categories: {str(e)}", 500

@app.route('/delete_records', methods=['POST'])
def delete_records():
    try:
        # Get form data
        record_ids_str = request.form.get('record_ids')
        
        if not record_ids_str:
            return "Missing record IDs", 400
            
        # Parse comma-separated record IDs
        record_ids = [id.strip() for id in record_ids_str.split(',') if id.strip()]
        
        if not record_ids:
            return "No valid record IDs provided", 400
            
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete records
        delete_query = """
            DELETE FROM processed_records 
            WHERE record_id_bank = ANY(%s)
        """
        cursor.execute(delete_query, (record_ids,))
        
        # Commit the changes
        conn.commit()
        
        # Close connections
        cursor.close()
        conn.close()
        
        return f"Successfully deleted {len(record_ids)} records", 200
        
    except Exception as e:
        logging.error(f"Error deleting records: {str(e)}")
        logging.debug("Traceback:")
        import traceback
        traceback.print_exc()
        return f"Error deleting records: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)