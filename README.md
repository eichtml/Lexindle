# 📚 Kindle Vocabulary to Anki Exporter 🌐

This Python script extracts words you've **looked up using the Kindle's Vocabulary Builder feature** and converts them into fully formatted Anki flashcards with context and automatic translations. It helps you build a personal vocabulary deck from your reading sessions, making language learning effortless and personalized.


---

## 🔍 What it does

- Parses your Kindle's `vocab.db` SQLite database
- Filters words by **frequency** (Zipf scale) or includes all
- Retrieves example sentences (contexts) from your reading
- Translates both the word and its contexts into your target language using Google Translate
- Generates an `.apkg` Anki package with clean styling


---

## 🛠️ How to get your `vocab.db` file from your Kindle

1. **Connect your Kindle to your computer** via USB.  
2. Open **File Explorer** and select the Kindle drive.  
3. To show hidden files on Windows (because `vocab.db` is hidden by default):  
   - Click on the **View** tab at the top of the File Explorer window.  
   - Check the box labeled **Hidden items** (this will show hidden files and folders).  
4. Navigate to the following folder on your Kindle: `system/vocabulary/vocab.db`
5. Copy the `vocab.db` file into the **same folder** where the script is located.  
6. (Optional) After copying, **uncheck** the **Hidden items** box to disable viewing hidden files again.

> ⚠️ If you don’t enable hidden files, you won’t be able to see the `vocab.db` file.
---

## 🤔 How it works (step-by-step)

When you run the script:
```bash
python lexindle.py
```
1. You can choose to include **all words** or filter them by **Zipf** frequency.

   If you select filtering by Zipf frequency, words are kept if they:

   - Have a Zipf frequency equal to or higher than the selected threshold (default is 3.0), or  
   - Appear at least twice in the Kindle vocabulary database.


   ### What is Zipf frequency?

   Zipf frequency is a measure of how common a word is in a language, based on the Zipf scale (ranging roughly from 0 to 10).  
   - Higher Zipf values mean the word is more common and likely easier to remember.  
   - Lower values indicate rare or specialized words.  

2. It analyzes and shows a split view of:  
   - ✅ Kept words (with frequency and context count)  
   - ❌ Discarded words (with frequency and context count)  

3. You choose your **target translation language** (e.g., `it` for Italian).

4. The script creates a local database to:  
   - Avoid duplicate words  
   - Track seen contexts  
   - Allow efficient re-runs  

5. For each word:  
   - The word and its contexts are translated using Google Translate  
   - Contexts are highlighted with the keyword  

6. It generates a stylized `.apkg` Anki file:  
   - Front: Word + context lines with bolded target word  
   - Back: Context translations + word translation
---

## 💾 Output

- Anki deck file: `Kindle_Vocab.apkg`
- Internal database: `db_lexindle.db` (do not delete if you plan to re-run or update)

---

## 🔁 Importing into Anki
Once the script generates the `Kindle_Vocab.apkg` file, you can **simply double-click** it to start the import process in Anki. In the import options window:
  - `Import any learning progress` — **enabled** 
  - `Import any deck presets` — **enabled** 
- Under **“Updates”**, set the following options:  

  - `Merge notetype changes` — **enabled**  

  - `Update notes` — **Always**  
  - `Update note types` — **Always**

Then click **Import** to complete the process.


Your Kindle vocabulary deck is now ready in Anki! 🎉

---

## 📦 Requirements

This project requires a few Python libraries. You can install them all at once using `pip` and the provided `requirements.txt` file.

### 🔧 Install dependencies

From the folder where the script is located, run:

```bash
pip install -r requirements.txt
```

## ⚠️ Important Kindle Vocabulary Limit

Your Kindle can store **a maximum of about 2000 vocabulary words**.  

If you approach this limit:  
- It's a good idea to **copy the `vocab.db` file to your computer** regularly to save your vocabulary progress.  
- Then, **delete the `vocab.db` file from your Kindle** to reset the vocabulary database and free up space for new words.  


To restore the vocabulary database on your Kindle:  
- Simply **create a new empty file named `vocab.db`** in the same folder on your Kindle.  
- **Restart your Kindle** to generate a fresh vocabulary database.

This way, you can keep collecting new words without losing old data saved on your computer.


## 🚀 Future Developments
- Integration with the **KOReader** vocabulary database.
- Translation powered by **Gemini AI** for more accurate and context-aware results.  
- **Statistics and analytics** on the words stored in your own vocabulary database (`db_lexindle.db`).

