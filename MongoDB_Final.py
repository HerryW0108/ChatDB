from pathlib import Path

import pandas as pd

import Mongo_execution as execution

PROJECT_DIR = Path(__file__).resolve().parent

# Load datasets for aggregation
def load_datasets():
    try:
        usercuisine = pd.read_csv(PROJECT_DIR / "usercuisine.csv")
        userpayment = pd.read_csv(PROJECT_DIR / "userpayment.csv")
        userprofile = pd.read_csv(PROJECT_DIR / "userprofile.csv")
        print("Datasets loaded successfully!")
        return {
            "usercuisine": usercuisine,
            "userpayment": userpayment,
            "userprofile": userprofile
        }
    except Exception as e:
        print(f"Error loading datasets: {e}")
        return None




# Function to select the dataset to work with
def select_dataset(datasets):
    print("\nAvailable datasets:")
    for i, dataset_name in enumerate(datasets.keys()):
        print(f"{i + 1}. {dataset_name}")

    while True:
        try:
            choice = int(input("\nSelect a dataset to work with (enter the number): ").strip())
            if 1 <= choice <= len(datasets):
                dataset_name = list(datasets.keys())[choice - 1]
                print(f"You selected: {dataset_name}")
                return datasets[dataset_name], dataset_name
            else:
                print("Invalid choice. Please select a valid dataset number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

# Load the dataset locally for find queries
def load_local_data(file_path):
    try:
        dataset_path = Path(file_path).expanduser()
        if not dataset_path.is_absolute():
            dataset_path = PROJECT_DIR / dataset_path
        data = pd.read_csv(dataset_path)
        print(f"Successfully loaded data from '{dataset_path}'.")
        return data
    except Exception as e:
        print(f"Error loading data from '{file_path}': {e}")
        return None

# Operator mapping for user-friendly input
operator_map = {
    "greater than": "$gt",
    "less than": "$lt",
    "equal to": "$eq",
    "greater than or equal to": "$gte",
    "less than or equal to": "$lte",
    "not equal to": "$ne",
    "in": "$in"
}


def is_text_field(series):
    """Return whether a Pandas series should accept string operators."""
    return not (
        pd.api.types.is_numeric_dtype(series.dtype)
        or pd.api.types.is_bool_dtype(series.dtype)
    )


def coerce_field_value(series, raw_value):
    """Convert CLI input to the type represented by a Pandas series."""
    value = raw_value.strip()
    if pd.api.types.is_bool_dtype(series.dtype):
        normalized_value = value.lower()
        if normalized_value in {"true", "false"}:
            return normalized_value == "true"
        raise ValueError("expected true or false")
    if pd.api.types.is_integer_dtype(series.dtype):
        return int(value)
    if pd.api.types.is_float_dtype(series.dtype):
        return float(value)
    return value


# Generate dynamic find query with multiple conditions
def generate_find_query(data, dataset_name):
    filter_query = {}
    projection_query = {}
    conditions = []

    available_fields = data.columns.tolist()

    operator_map = {
        "greater than": "$gt",
        "greater than or equal to": "$gte",
        "less than": "$lt",
        "less than or equal to": "$lte",
        "equal to": "$eq",
        "not equal to": "$ne",
        "contains": "$regex",
        "in": "$in"
    }

    while True:
        filter_field = input("Enter a field to filter by (or press Enter to skip): ").strip()
        if not filter_field:
            break

        matched_field = next((f for f in available_fields if f.lower() == filter_field.lower()), None)
        if not matched_field:
            print(f"Invalid field: '{filter_field}'. Please enter a valid field from the dataset.")
            continue

        filter_field = matched_field

        while True:
            operator_input = input("Enter operator (e.g., greater than, less than, equal to, not equal to, contains): ").strip().lower()
            operator = operator_map.get(operator_input, None)
            if operator:
                field_is_text = is_text_field(data[filter_field])
                if field_is_text and operator in ["$gt", "$gte", "$lt", "$lte"]:
                    print(f"Invalid operator '{operator_input}' for string field '{filter_field}'. Please use valid string operators.")
                    continue
                if not field_is_text and operator == "$regex":
                    print(f"Invalid operator '{operator_input}' for non-string field '{filter_field}'.")
                    continue
                break
            else:
                print(f"Invalid operator: '{operator_input}'. Please enter a valid operator.")

        if operator == "$in":
            values = input(f"Enter values for the filter (comma-separated) for {filter_field}: ").strip()
            try:
                values_list = [
                    coerce_field_value(data[filter_field], value)
                    for value in values.split(",")
                ]
            except ValueError as error:
                print(f"Invalid value for {filter_field}: {error}.")
                continue
            conditions.append({filter_field: {operator: values_list}})
        elif operator == "$regex":
            regex_value = input(f"Enter the string value for the filter (for {filter_field}): ").strip()
            conditions.append({filter_field: {operator: regex_value}})
        else:
            raw_value = input(f"Enter value for the filter (for {filter_field}): ").strip()
            try:
                value = coerce_field_value(data[filter_field], raw_value)
            except ValueError as error:
                print(f"Invalid value for {filter_field}: {error}.")
                continue

            if not field_is_text:
                conditions.append({filter_field: {operator: value}})
            else:
                if operator == "$eq":
                    conditions.append({filter_field: value})
                else:
                    conditions.append({filter_field: {operator: value}})

        more_conditions = input("Do you have more condition(s)? (yes/no): ").strip().lower()
        if more_conditions not in ['yes', 'y']:
            break

    if len(conditions) > 1:
        combine_operator = input("Do you want to combine conditions with AND or OR? (Enter 'AND' or 'OR'): ").strip().lower()
        filter_query = {"$or": conditions} if combine_operator == "or" else {"$and": conditions}
    elif len(conditions) == 1:
        filter_query = conditions[0]

    projection_fields = input("Enter fields to project (comma-separated, or press Enter to skip): ").strip()
    if projection_fields:
        fields = [field.strip() for field in projection_fields.split(",")]
        for field in fields:
            matched_field = next((f for f in available_fields if f.lower() == field.lower()), None)
            if not matched_field:
                print(f"Invalid field: '{field}'. Please enter a valid field from the dataset.")
                return None
            projection_query[matched_field] = 1

    return {
        "dataset": dataset_name,
        "filter": filter_query,
        "projection": projection_query if projection_query else None
    }


def generate_aggregate_query(dataset, dataset_name, datasets):
    pipeline = []
    print(f"Great! You're working with the dataset: {dataset_name}")
    print("Let's customize your query step by step!")

    # Initialize a variable to track joined dataset fields
    joined_fields = {}
    joined_datasets = {}  # Track the original fields from joined datasets

    # Initialize a list of valid fields
    valid_fields = list(dataset.columns)

    # Filter data (Match stage)
    while True:
        filter_data = input("Do you want to narrow down the data? (yes/no/skip): ").strip().lower()
        if filter_data in ["yes", "y"]:
            filter_field = input("What criteria should we use to narrow down the data (e.g., height)?: ").strip()
            if filter_field in valid_fields or filter_field in joined_fields:
                field_series = dataset[filter_field] if filter_field in dataset.columns else None
                field_is_text = is_text_field(field_series) if field_series is not None else True
                while True:
                    operator = input("How should we match the data? (e.g., equal to, greater than): ").strip().lower()
                    operator_key = operator_map.get(operator)

                    if operator_key is None:
                        print(f"Invalid operator: '{operator}'. Please enter a valid operator.")
                        continue

                    if field_is_text and operator_key in ["$gt", "$gte", "$lt", "$lte"]:
                        print(
                            f"Invalid operator '{operator}' for string field '{filter_field}'. Please use valid operators like 'equal to'.")
                        continue

                    break

                raw_value = input(f"What value should it match?: ").strip()

                if operator_key == "$in":
                    try:
                        value = [
                            coerce_field_value(field_series, item)
                            if field_series is not None
                            else item.strip()
                            for item in raw_value.split(",")
                        ]
                    except ValueError as error:
                        print(f"Invalid value for {filter_field}: {error}.")
                        continue
                elif field_series is not None:
                    try:
                        value = coerce_field_value(field_series, raw_value)
                    except ValueError as error:
                        print(f"Invalid value for {filter_field}: {error}.")
                        continue
                else:
                    value = raw_value

                pipeline.append({"$match": {filter_field: {operator_key: value}}})
            else:
                print(f"'{filter_field}' isn't a valid field in {dataset_name}. Please try again.")
        elif filter_data in ["no", "skip", "n"]:
            break
        else:
            print("Invalid input. Please enter 'yes', 'no', or 'skip'.")

    # Join with another dataset (Lookup stage)
    while True:
        join_data = input("Would you like to include data from another dataset? (yes/no/skip): ").strip().lower()
        if join_data in ["yes", "y"]:
            while True:
                join_dataset_name = input("Which dataset has the data you need?: ").strip()
                if join_dataset_name in datasets:
                    while True:
                        join_field = input("What common field links the two datasets?: ").strip()
                        if join_field in valid_fields or join_field in joined_fields:
                            output_field = input("What name should we give to the combined data?: ").strip()

                            # Perform the join
                            pipeline.append({
                                "$lookup": {
                                    "from": join_dataset_name,
                                    "localField": join_field,
                                    "foreignField": join_field,
                                    "as": output_field
                                }
                            })
                            pipeline.append({"$unwind": f"${output_field}"})

                            # Store the original fields from the joined dataset
                            joined_datasets[join_dataset_name] = {
                                'prefix': output_field,
                                'fields': list(datasets[join_dataset_name].columns)
                            }

                            # Add the joined fields to both tracking dictionaries
                            joined_columns = datasets[join_dataset_name].columns
                            for column in joined_columns:
                                if column != join_field:  # Avoid repeating the join field
                                    field_name = column  # Store original field name
                                    joined_fields[field_name] = f"${output_field}.{column}"
                                    valid_fields.append(field_name)  # Add original field name to valid fields

                            print(
                                f"Successfully joined '{join_dataset_name}' on '{join_field}'. You can now access fields from the joined dataset.")
                            break
                        else:
                            print(
                                f"'{join_field}' isn't a valid field in {dataset_name} or any joined dataset. Please try again.")
                    break
                else:
                    print(f"'{join_dataset_name}' isn't a valid dataset. Please try again.")
        elif join_data in ["no", "skip", "n"]:
            break
        else:
            print("Invalid input. Please enter 'yes', 'no', or 'skip'.")

    # Group data
    while True:
        group_data = input("Would you like to group the data? (yes/no/skip): ").strip().lower()
        if group_data in ["yes", "y"]:
            # Get grouping field
            group_field = input("Enter the field to group by (e.g., Rcuisine): ").strip()

            # Validate group field
            if group_field not in valid_fields and group_field not in joined_fields:
                print(f"Invalid field for grouping: {group_field}. Please try again.")
                continue

            # Initialize group stage
            group_stage = {}

            # Set the _id field for grouping
            if group_field in joined_fields:
                group_stage["_id"] = joined_fields[group_field]
            else:
                group_stage["_id"] = f"${group_field}"

            # Get aggregation operations
            print("\nAvailable aggregation operations:")
            print("1. count - Count number of documents")
            print("2. sum - Sum values in a field")
            print("3. avg - Calculate average of a field")
            print("4. min - Find minimum value in a field")
            print("5. max - Find maximum value in a field")

            aggregation_fields = {}  # Store fields that were aggregated

            while True:
                operation = input("\nSelect an aggregation operation (or press Enter to finish): ").strip().lower()
                if not operation:
                    break

                if operation in ["count", "1"]:
                    output_field = input("Enter the name for the count field (e.g., count): ").strip()
                    group_stage[output_field] = {"$sum": 1}
                    aggregation_fields[output_field] = "$" + output_field

                elif operation in ["sum", "2", "avg", "3", "min", "4", "max", "5"]:
                    field_to_aggregate = input("Which field should we aggregate?: ").strip()
                    if field_to_aggregate not in valid_fields and field_to_aggregate not in joined_fields:
                        print(f"Invalid field: {field_to_aggregate}")
                        continue

                    output_field = input("Enter the name for the aggregated field: ").strip()

                    field_path = joined_fields.get(field_to_aggregate, f"${field_to_aggregate}")

                    if operation in ["sum", "2"]:
                        group_stage[output_field] = {"$sum": field_path}
                    elif operation in ["avg", "3"]:
                        group_stage[output_field] = {"$avg": field_path}
                    elif operation in ["min", "4"]:
                        group_stage[output_field] = {"$min": field_path}
                    elif operation in ["max", "5"]:
                        group_stage[output_field] = {"$max": field_path}

                    aggregation_fields[output_field] = "$" + output_field

                else:
                    print("Invalid operation. Please select a valid operation.")
                    continue

                more_operations = input("Add another aggregation operation? (yes/no): ").strip().lower()
                if more_operations not in ["yes", "y"]:
                    break

            pipeline.append({"$group": group_stage})

            # Add a project stage after grouping to properly format the output
            project_stage = {
                "_id": 0,
                group_field: "$_id"  # This will show the group field value (e.g., cuisine name)
            }
            # Add all aggregated fields to the projection with their chosen names
            for field, value in aggregation_fields.items():
                project_stage[field] = value

            pipeline.append({"$project": project_stage})

            # Update valid_fields for sort stage
            valid_fields = list(project_stage.keys())
            if "_id" in valid_fields:
                valid_fields.remove("_id")

            break

        elif group_data in ["no", "skip", "n"]:
            break
        else:
            print("Invalid input. Please enter 'yes', 'no', or 'skip'.")

    # Sort functionality
    while True:
        sort_data = input("Would you like to sort the results? (yes/no/skip): ").strip().lower()
        if sort_data in ["yes", "y"]:
            sort_stage = {}

            while True:
                print(f"\nAvailable fields for sorting: {', '.join(valid_fields)}")
                sort_field = input("Which field would you like to sort by?: ").strip()

                if sort_field in valid_fields:
                    sort_order = input("Sort in ascending (1) or descending (-1) order? Enter 1 or -1: ").strip()
                    if sort_order in ["1", "-1"]:
                        sort_stage[sort_field] = int(sort_order)

                        more_sort = input("Would you like to add another sort field? (yes/no): ").strip().lower()
                        if more_sort not in ["yes", "y"]:
                            break
                    else:
                        print("Invalid sort order. Please enter 1 for ascending or -1 for descending.")
                else:
                    print(f"Field '{sort_field}' not found in the available fields.")
                    retry = input("Would you like to try another field? (yes/no): ").strip().lower()
                    if retry not in ["yes", "y"]:
                        break

            if sort_stage:
                pipeline.append({"$sort": sort_stage})

        elif sort_data in ["no", "skip", "n"]:
            break
        else:
            print("Invalid input. Please enter 'yes', 'no', or 'skip'.")

    # Limit functionality
    while True:
        limit_data = input("Would you like to limit the number of results? (yes/no/skip): ").strip().lower()
        if limit_data in ["yes", "y"]:
            while True:
                try:
                    limit_value = int(input("Enter the maximum number of results you want to see: ").strip())
                    if limit_value > 0:
                        pipeline.append({"$limit": limit_value})
                        break
                    else:
                        print("Please enter a positive number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            break
        elif limit_data in ["no", "skip", "n"]:
            break
        else:
            print("Invalid input. Please enter 'yes', 'no', or 'skip'.")

    # Project fields at the end
    while True:
        retrieve_fields = input(
            "What specific details do you want to see in the results (e.g. userID, height)?: ").strip()
        fields = [field.strip() for field in retrieve_fields.split(",")]

        # Validate fields considering both original and joined fields
        invalid_fields = []
        for field in fields:
            if field not in valid_fields and field not in joined_fields:
                invalid_fields.append(field)

        if not invalid_fields:
            project_stage = {}
            for field in fields:
                if field in joined_fields:
                    # If it's a joined field, use the proper prefix
                    project_stage[f"joined_{field}"] = joined_fields[field]
                else:
                    # If it's an original field from the main dataset
                    project_stage[field] = f"${field}"

            project_stage["_id"] = 0  # Exclude MongoDB's default _id field
            pipeline.append({"$project": project_stage})
            break
        else:
            print(f"Invalid fields: {', '.join(invalid_fields)}. Please enter valid fields.")

    # Return the aggregation pipeline list
    return pipeline


# # Generate random examples
# def generate_random_example(input_type):
#     examples = {
#         "example find functions": [
#             "db.users.find({})",
#             "db.products.find({})",
#             "db.orders.find({})"
#         ],
#         "example aggregate function": [
#             "db.users.aggregate([{$group: {_id: '$city', count: {$sum: 1}}}])",
#             "db.orders.aggregate([{$group: {_id: '$status', total: {$sum: '$amount'}}}])"
#         ],
#         "example find function with query criteria": [
#             "db.users.find({age: {$gt: 25}})",
#             "db.products.find({price: {$lt: 100}})"
#         ],
#         "example find function with projection": [
#             "db.users.find({}, {name: 1, age: 1, _id: 0})",
#             "db.products.find({}, {name: 1, price: 1, _id: 0})"
#         ],
#         "example find functions with multiple conditions (and/or)": [
#             "db.users.find({$and: [{age: {$gt: 25}}, {city: 'New York'}]})",
#             "db.orders.find({$or: [{status: 'shipped'}, {status: 'pending'}]})"
#         ]
#     }
#     for key, value in examples.items():
#         if key in input_type.lower():
#             return random.choice(value)
#     return "No examples available for this input type."


def generate_example_queries(datasets, selected_dataset=None, query_type=None):
    """
    Dynamically generate example MongoDB queries based on available datasets and their fields.
    """
    # Check if datasets is None or empty
    if not datasets:
        print("Error: No datasets available. Please make sure the datasets are properly loaded.")
        return []

    import random

    def get_random_field(df, exclude_fields=None):
        """Get a random field from DataFrame excluding specified fields"""
        fields = list(df.columns)
        if exclude_fields:
            fields = [f for f in fields if f not in exclude_fields]
        return random.choice(fields) if fields else None

    def get_field_value(df, field):
        """Get a random value from a DataFrame field"""
        try:
            return random.choice(df[field].dropna().unique())
        except:
            return None

    examples = []

    try:
        # If specific dataset selected, only use that one
        if selected_dataset and selected_dataset in datasets:
            working_datasets = {selected_dataset: datasets[selected_dataset]}
        else:
            working_datasets = datasets

        for dataset_name, df in working_datasets.items():
            # Generate Find Examples
            if not query_type or query_type == "find":
                # Generate find queries with conditions
                for _ in range(3):  # Generate multiple examples per dataset
                    field = get_random_field(df)
                    if field:
                        value = get_field_value(df, field)
                        if value is not None:
                            # Get random additional fields for projection
                            other_fields = random.sample([f for f in df.columns if f != field],
                                                       min(2, len(df.columns) - 1))
                            projection = {f: 1 for f in [field] + other_fields}
                            projection["_id"] = 0

                            if isinstance(value, (int, float)):
                                # Generate numeric comparison
                                operator = random.choice(["$eq", "$gt", "$lt", "$gte", "$lte"])
                                examples.append({
                                    "description": f"Find with numeric {operator} condition on {dataset_name}",
                                    "query": f'db.{dataset_name}.find({{"{field}": {{"{operator}": {value}}}}}, {projection})',
                                    "explanation": f"Finds records in {dataset_name} where {field} {operator.replace('$', '')} {value}, showing fields: {', '.join([field] + other_fields)}"
                                })
                            else:
                                # Generate string comparison
                                examples.append({
                                    "description": f"Find with condition on {dataset_name}",
                                    "query": f'db.{dataset_name}.find({{"{field}": "{value}"}}, {projection})',
                                    "explanation": f"Finds records in {dataset_name} where {field} equals '{value}', showing fields: {', '.join([field] + other_fields)}"
                                })

            # Generate Aggregate Examples
            if not query_type or query_type == "aggregate":
                numeric_fields = df.select_dtypes(include=['int64', 'float64']).columns
                if len(numeric_fields) > 0:
                    # Group by with count and filtering
                    group_field = get_random_field(df)
                    if group_field:
                        # Add a match stage before grouping
                        match_field = get_random_field(df, [group_field])
                        match_value = get_field_value(df, match_field) if match_field else None

                        if match_value is not None:
                            examples.append({
                                "description": f"Filtered aggregation with group by on {dataset_name}",
                                "query": f'''db.{dataset_name}.aggregate([
    {{"$match": {{"{match_field}": "{match_value}"}}}},
    {{"$group": {{
        "_id": "${group_field}",
        "count": {{"$sum": 1}}
    }}}},
    {{"$sort": {{"count": -1}}}}
])''',
                                "explanation": f"Groups records by {group_field} where {match_field} equals '{match_value}', counts occurrences, and sorts by count"
                            })

                    # Advanced aggregation with multiple stages
                    agg_field = random.choice(numeric_fields) if numeric_fields.size > 0 else None
                    if group_field and agg_field and agg_field != group_field:
                        examples.append({
                            "description": f"Advanced multi-stage aggregation on {dataset_name}",
                            "query": f'''db.{dataset_name}.aggregate([
    {{"$group": {{
        "_id": "${group_field}",
        "count": {{"$sum": 1}},
        "avg_{agg_field}": {{"$avg": "${agg_field}"}},
        "max_{agg_field}": {{"$max": "${agg_field}"}}
    }}}},
    {{"$match": {{"count": {{"$gt": 1}}}}}},
    {{"$sort": {{"avg_{agg_field}": -1}}}}
])''',
                            "explanation": f"Groups by {group_field}, calculates stats for {agg_field}, filters groups with count > 1, sorts by average"
                        })

        # Randomly select a subset of examples
        if examples:
            num_examples = min(random.randint(3, 5), len(examples))
            return random.sample(examples, num_examples)
        else:
            print("No examples could be generated. Please check your datasets and query type.")
            return []

    except Exception as e:
        print(f"Error generating examples: {e}")
        return []



def display_example_queries(examples):
    """
    Display the example queries in a formatted way and handle user selection.

    Args:
        examples (list): List of example query dictionaries

    Returns:
        str or None: Selected query string if user chooses to execute one, None otherwise
    """
    # Display examples
    print("\n=== MongoDB Query Examples ===\n")
    for i, example in enumerate(examples, 1):
        print(f"Example {i}: {example['description']}")
        print("Query:")
        print(example['query'])
        print("\nExplanation:", example['explanation'])
        print("\n" + "="*50 + "\n")

    # Handle user selection
    try_example = input("\nWould you like to execute any of these examples? (yes/no): ").strip().lower()
    if try_example == "yes":
        while True:
            example_num = input("Enter the example number to execute (or 0 to cancel): ").strip()
            if example_num == "0":
                return None

            if example_num.isdigit() and 1 <= int(example_num) <= len(examples):
                selected_query = examples[int(example_num) - 1]['query']
                print(f"\nSelected query: {selected_query}")
                return selected_query
            else:
                print(f"Invalid example number. Please enter a number between 1 and {len(examples)}")

    return None





# Chat interface
def chat_with_user():
    print("Welcome to ChatDB! Type 'find', 'aggregate', 'example', or 'quit' to exit.")
    datasets = None
    data = None
    dataset_name = None

    while True:
        question = input("\nAsk a question (e.g., 'find', 'aggregate', 'example', or 'quit'): ").strip().lower()
        if question in ["quit", "exit"]:
            print("Goodbye!")
            break
        elif question == "find":
            file_path = input("Enter the file path for your dataset (CSV): ").strip()
            data = load_local_data(file_path)
            if data is None:
                continue

            query = generate_find_query(data, Path(file_path).stem)
            if not query:
                continue

            # Generated MongoDB Query
            generated_query = ""
            print("\nGenerated Query:")
            if query["projection"]:
                generated_query = f'db.{query["dataset"]}.find({query["filter"]}, {query["projection"]})'
            else:
                generated_query = f'db.{query["dataset"]}.find({query["filter"]})'
            print(generated_query)

            # Ask if the user wants to execute the query
            apply_code = input("Do you want to apply this MongoDB code on dataset? (yes/no): ").strip().lower()
            if apply_code == "yes":
                execution.execute_find(generated_query)

        elif question == "aggregate":
            if datasets is None:
                datasets = load_datasets()
                if datasets is None:
                    continue

            data, dataset_name = select_dataset(datasets)
            if data is None:
                continue

            pipeline = generate_aggregate_query(data, dataset_name, datasets)
            if not pipeline:
                continue

            # Generated Aggregation Pipeline
            print("\nGenerated Aggregation Pipeline:")
            print(f'db.{dataset_name}.aggregate({pipeline})')

            # Ask if the user wants to execute the aggregation
            apply_code = input("Do you want to apply this MongoDB code on dataset? (yes/no): ").strip().lower()
            if apply_code == "yes":
                execution.execute_aggregate(dataset_name, pipeline)  # Pass the dataset name and pipeline directly

        # elif question == "example":
        #     example_type = input("Enter example type (e.g., 'example find functions'): ").strip().lower()
        #     example = generate_example_queries(example_type)
        #     print("\nExample:")
        #     print(example)


        elif question == "example":
            # First, ensure datasets are loaded
            if datasets is None:
                print("\nLoading datasets...")
                datasets = load_datasets()
                if datasets is None:
                    print("Error: Failed to load datasets. Please check if all dataset files exist.")
                    continue

            # Get example type preference from user
            print("\nAvailable example types:")
            print("1. Example Find queries")
            print("2. Example Aggregate queries")
            print("3. Dataset-specific queries")

            while True:
                example_choice = input("\nChoose example type (1-3): ").strip()
                if example_choice in ["1", "2", "3"]:
                    break
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")

            selected_dataset = None
            if example_choice == "3":
                print("\nAvailable datasets:")
                for i, name in enumerate(datasets.keys(), 1):
                    print(f"{i}. {name}")
                dataset_choice = input("\nSelect dataset number or press Enter for all: ").strip()
                if dataset_choice.isdigit() and 1 <= int(dataset_choice) <= len(datasets):
                    selected_dataset = list(datasets.keys())[int(dataset_choice) - 1]

            # Generate examples based on choice
            try:
                if example_choice == "1":  # Find queries
                    examples = generate_example_queries(datasets, selected_dataset, query_type="find")
                    if examples:
                        example_query = display_example_queries(examples)
                        if example_query:  # Only proceed if a query was selected
                            apply_code = input("Do you want to apply this MongoDB code on dataset? (yes/no): ").strip().lower()
                            if apply_code == "yes":
                                execution.execute_find(example_query)

                elif example_choice == "2":  # Aggregate queries
                    examples = generate_example_queries(datasets, selected_dataset, query_type="aggregate")
                    if examples:
                        example_query = display_example_queries(examples)
                        if example_query:  # Only proceed if a query was selected
                            # Extract collection name and pipeline from the aggregate query
                            dataset_name = example_query.split('.')[1].split('.')[0]
                            pipeline_str = example_query.split('aggregate(')[1].rstrip(')')
                            import ast
                            pipeline = ast.literal_eval(pipeline_str)

                            apply_code = input("Do you want to apply this MongoDB code on dataset? (yes/no): ").strip().lower()
                            if apply_code == "yes":
                                execution.execute_aggregate(dataset_name, pipeline)

                elif example_choice == "3":  # Dataset-specific queries
                    examples = generate_example_queries(datasets, selected_dataset)
                    if examples:
                        example_query = display_example_queries(examples)
                        if example_query:  # Only proceed if a query was selected
                            if "aggregate" in example_query:
                                dataset_name = example_query.split('.')[1].split('.')[0]
                                pipeline_str = example_query.split('aggregate(')[1].rstrip(')')
                                import ast
                                pipeline = ast.literal_eval(pipeline_str)

                                apply_code = input("Do you want to apply this MongoDB code on dataset? (yes/no): ").strip().lower()
                                if apply_code == "yes":
                                    execution.execute_aggregate(dataset_name, pipeline)
                            else:
                                apply_code = input("Do you want to apply this MongoDB code on dataset? (yes/no): ").strip().lower()
                                if apply_code == "yes":
                                    execution.execute_find(example_query)
            except Exception as e:
                print(f"Error processing example: {e}")
                continue
            # apply_code = input("Do you want to apply this MongoDB code on dataset? (yes/no): ").strip().lower()
            # if apply_code == "yes":
            #     import execution
            #     execution.execute_find(generated_query)

        else:
            print("Invalid option. Try again.")



# Main entry
if __name__ == "__main__":
    chat_with_user()
