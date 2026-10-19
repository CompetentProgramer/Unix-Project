Steps to set up dashboard
1. Find the host machines global ip either use a website or the cmd line
2. Initialize the 4 servers using the guide in the GitHub codebase (Ensuring you added your ip address to each server)
3. Copy the respective API URLs and API keys into the APICaller.py
4. Ensure you have tkinter, matplotlib, numpy, requests, and collection installed (use pip install if you don't have them)
5. run Dashboard.py

Debug Steps: If an error occurres
1. Comment out Dashboard.py -> line 340: app.UpdateProcess()
2. If the program still fails ensure you have all required libraries and try again
3. When it works with out the commented line; add the line back and ensure the API URLs and Keys are set correctly
  3a. If you are getting a 4xx error code you likely have the wrong api keys or the server does not have your host ip attached
  3b. if you are getting a time out error you likely have the wrong server ip or port: it should look like this "http://127.0.0.1:8090" replace the 127.0.0.1 with the serve global ip
