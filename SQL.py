import os
import mysql.connector
import random
import nltk
from nltk.tokenize import word_tokenize


def quote_identifier(identifier):
    """Quote a MySQL identifier and escape embedded backticks."""
    return f"`{identifier.replace('`', '``')}`"


def connect_to_sql_database():
    """Establish a connection to the MySQL database."""
    try:
        host = os.getenv("MYSQL_HOST", "localhost")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", "")
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
        )
        print("Connected to the MySQL server.")
        return conn
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            print("Error: Invalid username or password.")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            print("Error: Database does not exist.")
        else:
            print(f"Error connecting to the MySQL server: {err}")
        return None


def list_databases(conn):
    """List all available databases in MySQL."""
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES;")
        databases = [db[0] for db in cursor.fetchall()]
        print("\nAvailable Databases:")
        for db in databases:
            print(f" - {db}")
        return databases
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return []


def explore_database(conn, database_name):
    """Explore the database and display its table contents."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {quote_identifier(database_name)};")
        cursor.execute("SHOW TABLES;")
        tables = [table[0] for table in cursor.fetchall()]
        if not tables:
            print(f"The database '{database_name}' has no tables.")
            return None

        table_info = {}
        print(f"\nExploring '{database_name}' database:")
        for table_name in tables:
            cursor.execute(f"DESCRIBE {quote_identifier(table_name)};")
            columns = [col[0] for col in cursor.fetchall()]
            table_info[table_name] = columns

        print("\nTables in the database:")
        for table_name in tables:
            print(f" - {table_name}")

        # Allow the user to explore specific tables
        while True:
            print("\nEnter a table name to explore it, or type 'back' to return to the main menu:")
            choice = input("Your choice: ").strip()
            if choice.lower() == "back":
                break
            elif choice in table_info:
                explore_table(conn, database_name, choice)
            else:
                print("Invalid table name. Please try again.")

        return table_info
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return None


def explore_table(conn, database_name, table_name):
    """Explore a specific table and display its structure and sample data."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {quote_identifier(database_name)};")
        print(f"\nExploring table: {table_name}")

        # Fetch and display column details
        cursor.execute(f"DESCRIBE {quote_identifier(table_name)};")
        columns = cursor.fetchall()
        print("Columns:")
        for col in columns:
            print(f" - {col[0]} ({col[1]})")

        # Fetch and display sample rows
        cursor.execute(f"SELECT * FROM {quote_identifier(table_name)} LIMIT 5;")
        rows = cursor.fetchall()
        if rows:
            print("\nSample Rows:")
            for row in rows:
                print(row)
        else:
            print("\nThe table is empty.")

    except mysql.connector.Error as e:
        print(f"Error exploring table {table_name}: {e}")


def generate_specific_query(table_info, query_type):
    """Generate a specific type of SQL query."""
    if query_type == "select":
        return generate_select_query(table_info)
    elif query_type == "group by":
        return generate_group_by_query(table_info)
    elif query_type == "join":
        return generate_join_query(table_info)
    elif query_type == "where":
        return generate_where_query(table_info)
    else:
        return f"-- Unsupported query type: {query_type}"


def generate_random_query(table_info):
    """Generate a random SQL query from available types."""
    query_type = random.choice(["select", "group by", "join", "where"])
    return generate_specific_query(table_info, query_type)


def generate_select_query(table_info):
    """Generate a SELECT query."""
    table_name = random.choice(list(table_info.keys()))
    columns = table_info[table_name]
    selected_columns = random.sample(columns, min(len(columns), 2))
    selected_columns_sql = ", ".join(
        quote_identifier(column) for column in selected_columns
    )
    return f"SELECT {selected_columns_sql} FROM {quote_identifier(table_name)};"


def generate_group_by_query(table_info):
    """Generate a GROUP BY query."""
    table_name = random.choice(list(table_info.keys()))
    columns = table_info[table_name]
    group_by_column = random.choice(columns)
    agg_column = random.choice(columns)
    agg_function = random.choice(['SUM', 'AVG', 'COUNT'])
    group_by_sql = quote_identifier(group_by_column)
    aggregate_sql = quote_identifier(agg_column)
    table_sql = quote_identifier(table_name)
    return (
        f"SELECT {group_by_sql}, {agg_function}({aggregate_sql}) "
        f"FROM {table_sql} GROUP BY {group_by_sql};"
    )


def generate_where_query(table_info):
    """Generate a WHERE query."""
    table_name = random.choice(list(table_info.keys()))
    columns = table_info[table_name]
    where_column = random.choice(columns)
    where_value = random.choice([str(random.randint(1, 100)), "'sample_value'"])
    return (
        f"SELECT * FROM {quote_identifier(table_name)} "
        f"WHERE {quote_identifier(where_column)} = {where_value};"
    )


def generate_join_query(table_info):
    """Generate a JOIN query."""
    tables = list(table_info.keys())
    if len(tables) < 2:
        return "-- Not enough tables to generate a JOIN query."

    table1, table2 = random.sample(tables, 2)
    join_column1 = random.choice(table_info[table1])
    join_column2 = random.choice(table_info[table2])
    table1_sql = quote_identifier(table1)
    table2_sql = quote_identifier(table2)
    join_column1_sql = quote_identifier(join_column1)
    join_column2_sql = quote_identifier(join_column2)
    return (
        f"SELECT * FROM {table1_sql} JOIN {table2_sql} "
        f"ON {table1_sql}.{join_column1_sql} = "
        f"{table2_sql}.{join_column2_sql};"
    )


def execute_query(conn, database_name, query):
    """Execute a given query and display results."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {quote_identifier(database_name)};")
        cursor.execute(query)
        results = cursor.fetchall()
        if results:
            print("\nQuery Results:")
            for row in results:
                print(row)
        else:
            print("Query executed successfully. No rows returned.")
    except mysql.connector.Error as e:
        print(f"Error executing query: {e}")


def detect_query_type(user_input):
    """Use NLP to detect the query type from user input."""
    tokens = word_tokenize(user_input.lower())
    if "group by" in user_input or "group" in tokens:
        return "group by"
    elif "join" in tokens:
        return "join"
    elif "select" in tokens:
        return "select"
    elif "where" in tokens:
        return "where"
    else:
        return None


def run_SQL():
    """Handle user interaction, allowing them to explore databases and input custom queries."""
    print("This section is for Structured Query Languages (SQL)")
    conn = connect_to_sql_database()
    if not conn:
        return

    table_info = None

    while True:
        print("\nOptions:")
        print("1. List all available databases")
        print("2. Explore a database")
        print("3. Generate a specific SQL query")
        print("4. Generate a random SQL query")
        print("5. Exit")
        choice = input("\nEnter your choice: ").strip()

        if choice == '1':
            list_databases(conn)
        elif choice == '2':
            db_name = input("Enter the database name: ").strip()
            table_info = explore_database(conn, db_name)
        elif choice == '3':
            if not table_info:
                print("Please explore a database first to load table information.")
                continue

            print("\nDescribe the type of query you want (e.g., 'I want a GROUP BY query').")
            user_input = input("Your input: ")
            query_type = detect_query_type(user_input)

            if query_type:
                query = generate_specific_query(table_info, query_type)
                print("\nGenerated Query:")
                print(query)

                execute_choice = input("\nDo you want to execute this query? (yes/no): ").strip().lower()
                if execute_choice in ['yes', 'y']:
                    execute_query(conn, db_name, query)
            else:
                print("Sorry, I couldn't understand the type of query you want.")
        elif choice == '4':
            if not table_info:
                print("Please explore a database first to load table information.")
                continue

            query = generate_random_query(table_info)
            print("\nGenerated Query:")
            print(query)

            execute_choice = input("\nDo you want to execute this query? (yes/no): ").strip().lower()
            if execute_choice in ['yes', 'y']:
                execute_query(conn, db_name, query)
        elif choice == '5':
            print("Returning to the main menu.")
            conn.close()
            return
        else:
            print("Invalid choice. Please try again.")
