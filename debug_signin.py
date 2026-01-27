from app import app, db
from models.book import User, Shelf, Book

with app.app_context():
    # Get user by email
    user = User.query.filter_by(email="balakishore5511@gmail.com").first()
    
    if user:
        print(f"User: {user.name} (ID: {user.id})")
        
        # Get shelves - try both user_id types
        shelves_by_id = Shelf.query.filter_by(user_id=user.id).all()
        shelves_by_email = Shelf.query.filter_by(user_id=user.email).all()
        
        print(f"\nShelves by user_id (integer): {len(shelves_by_id)}")
        for shelf in shelves_by_id:
            print(f"  - {shelf.shelf_name}: {len(shelf.books)} books")
            for book in shelf.books:
                print(f"      • {book.book_name}")
        
        print(f"\nShelves by user_id (email): {len(shelves_by_email)}")
        for shelf in shelves_by_email:
            print(f"  - {shelf.shelf_name}: {len(shelf.books)} books")
            for book in shelf.books:
                print(f"      • {book.book_name}")
        
        # Get ALL books in database
        all_books = Book.query.all()
        print(f"\nTotal books in database: {len(all_books)}")
    else:
        print("User not found")