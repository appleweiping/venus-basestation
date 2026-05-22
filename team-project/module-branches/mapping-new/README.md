# 🚀 Software Development Guide
 **Read this document carefully and follow it exactly.** 

If you skip a step, your code will not upload to the PYNQ board, and it will not run.

---

## 🛠️ Phase 1: First-Time Setup (Do this EXACTLY ONCE)

Before you write a single line of code, you must set up your laptop.

### Step 1: Install Required VS Code Extensions
1. Open VS Code.
2. Look at the far-left sidebar and click the **Extensions** icon.
3. In the search bar at the top, type `SFTP`. Look for the one by **Natizyskunk** and click **Install**.

## SSH Security Setup ("Password-Free" Connection)
Since we use TU/e Single Sign-On (SSO), standard passwords do not work with the Git terminal. We use SSH keys to identify your laptop.

### 1. Generate your Key
1. Open **PowerShell** on your Windows laptop or Terminal on Mac
2. Paste this command and press **Enter**:
   `ssh-keygen -t ed25519 -C "your_email@student.tue.nl"`
3. When it says "Enter file in which to save the key," **Press Enter** to stay with the default.
4. When it asks for a passphrase, **Press Enter** (leave it empty). Press **Enter** again to confirm.
   *(You should see a "randomart" box made of symbols—this means it worked).*

### 2. Copy the Key to GitLab
1. In the same PowerShell / Terminal window, paste this command to show your key:
   `cat ~/.ssh/id_ed25519.pub`
2. Highlight the entire block of text that starts with `ssh-ed25519` and ends with your email. **Right-click** to copy it.
3. Go to [GitLab.tue.nl](https://gitlab.tue.nl). 
4. Click your **Profile Icon** (top-right) -> **Edit Profile**.
5. On the left-side menu, click **SSH Keys**.
6. Click the **Add new key** button.
7. Paste your key into the **Key** text box.
8. Click **Add key** at the bottom.
9. You should now be able to click on the code button on top of the repository and enter VSCODE

### Step 3: Create Your Connection
The setup allows auto-sync so your code goes automatically to the PYNQ board when you save (if you're connected with an ethernet cable offcourse). You need to tell it your name so it doesn't overwrite your someone else's work.

1. In the left sidebar, open the `.vscode` folder.
2. Find the file named `sftp.json.example`.
3. **Right-click** `sftp.json.example` and click **Copy**. **DO NOT DELETE THAT FILE!**
4. **Right-click** anywhere inside the `.vscode` folder and click **Paste**.
5. Right-click the new copied file and **Rename** it to exactly: `sftp.json`
6. Open your new `sftp.json` file.
7. Look for the line that says: `"remotePath": "/home/student/CHANGE_ME",`
8. Replace `CHANGE_ME` with your actual first name (all lowercase). 
9. Press **`Ctrl + S`** (or `Cmd + S` on Mac) to save the file. 

*(Note: Git is programmed to ignore this file. Do not worry if you don't see it in your Source Control tab).*

---

## 💻 Phase 2: Daily Workflow (How to write code)

**CRITICAL RULE:** Never write code directly on the `main` branch. 

### Step 1: Select your branch
1. On VS Code go the bottom left and click on the text that says 'main'
2. Choose one of the three branches you're working on


### Step 2: Write and Auto-Sync
1. Open any `.c` or `.h` file and start coding.
2. Whenever you are done typing, press **`Ctrl + S`** to save.
3. Look at the bottom-left corner of your VS Code window. A tiny green loading bar will appear. That means your file was successfully uploaded to your personal folder on the PYNQ board if you're connected.
4. Your changes are always synced to your computer.
**You never have to manually drag, drop, or copy files.**

### Step 3: Syncing your code to GitLab
It's important you sync to GitLab so everyone can receive your changes on their laptop
1. After you are done changing your code click on source control in the VS Code sidebar (below the search icon)
2. Enter a short message of what you change in the text box that says "commit message"
3. Click commit and follow the instructions. This updates your local version of the repository
4. Click sync to udpate the online repository with your local version
5. YOU SHOULD NEVER COMMIT CHANGES TO THE MAIN BRANCH ALWAYS CHECK THE BOTTOM OF THE VSCODE PAGE TO MAKE SURE YOU ARE ON YOU'RE MODULE'S BRANCH
---

## 🏃 Phase 3: Running Your Code on the Hardware

### Step 1: Open the PYNQ Terminal
1. Press ctrl and ~
2. A terminal will open.
3. Click the plus icon above it and select PYNQ-board
3. Type `student` and press Enter. *(You will not see the letters appear as you type. This is normal).*

### Step 3: Compile and Run
1. Use cd to go to your own directory. (Eg cd libpynq/dennis/libpynq-5EID..BLAHBLAHBLAH/applications/test/)
2. Type `make` and press Enter to compile.
3. If there are no errors, run your executable. (make run or ./main)

---

## 🏁 Phase 4: Finishing Your Task

### Create a Merge Request
1. Go to GitLab in your web browser.
2. Click **Create Merge Request** for your branch.
3. **🚨 CRITICAL:** Scroll down to the bottom of the page and **UNCHECK** the box that says *"Delete source branch when merge request is accepted."* 
4. Click **Merge**.