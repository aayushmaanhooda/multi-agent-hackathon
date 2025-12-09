
import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure current directory is in sys.path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Run the app
    # reload=True works best when the app string is a package path
    uvicorn.run("app.api:app", host="localhost", port=8000, reload=True)
