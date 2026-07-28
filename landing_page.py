def greet_user():
    """Display the main menu and route the user to a database workflow."""
    while True:
        print("\nWelcome to ChatDB!")
        print("1. Explore SQL databases")
        print("2. Explore MongoDB")
        print("3. Exit")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            from SQL import run_SQL

            run_SQL()
        elif choice == "2":
            from MongoDB_Final import chat_with_user

            chat_with_user()
        elif choice == "3":
            print("Goodbye!")
            return
        else:
            print("Invalid choice. Please try again.")
