# Making the live link (free)

1. Create a free GitHub account and a new **public** repository named `gold-tracker-india`.
2. Upload every file and folder from this project (drag them into the "Add file → Upload files" page).
3. Go to share.streamlit.io and sign in with GitHub.
4. Click **Create app**, pick your repository, set the main file to `app.py`, then open **Advanced settings**.
5. In the **Secrets** box paste this line with your real key: `FRED_API_KEY = "yourkeyhere"`
6. Click **Deploy**. After a few minutes you get a link like `yourname-gold-tracker.streamlit.app`.
7. Put that link and the GitHub link on your CV and LinkedIn.

Never upload your key to GitHub. It goes only in the Secrets box. The `.gitignore` file already protects a local secrets file.
