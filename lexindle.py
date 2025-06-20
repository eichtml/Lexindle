import os
import sqlite3
from wordfreq import zipf_frequency
from collections import defaultdict
from tabulate import tabulate
import genanki
from deep_translator import GoogleTranslator
from tqdm import tqdm
import hashlib

model = genanki.Model(
    model_id=2059400111,
    name='Kindle Vocabulary Model',
    fields=[
        {'name': 'Front'},
        {'name': 'Back'},
        {'name': 'Word'}
    ],
    templates=[
        {
            'name': 'Card Template',
            'qfmt': '{{Front}}',
            'afmt': '{{Front}}<hr id="answer">{{Back}}',
        }
    ],
css="""
.card {
  font-family: Arial;
  font-size: 20px;
  text-align: left;
  color: black;
  background-color: white;
  padding: 15px;
  line-height: 1.3;
}
.word-header {
  font-size: 24px;
  font-weight: bold;
  color: darkblue;
  margin-bottom: 12px;
}
b {
  color: navy;
  font-weight: bold;
}
.context-line {
  margin-bottom: 8px;
}
.translated-line {
  font-style: italic;
  color: #555;
  margin-bottom: 8px;
}
.word-translation {
  margin-top: 15px;
  font-weight: bold;
  font-size: 18px;
  color: darkgreen;
}
hr {
  margin-top: 20px;
  margin-bottom: 20px;
}
"""

)

def find_db_in_script_folder(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, filename)
    return db_path if os.path.isfile(db_path) else None

def detect_kindle_db_type(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = set(name.lower() for (name,) in cursor.fetchall())
        if 'words' in tables and 'lookups' in tables:
            return 'kindle'
        raise ValueError("Unrecognized DB format.")
    

def print_two_tables_side_by_side(table1, headers1, table2, headers2, title1="Words kept", title2="Words discarded", padding=4):

    table1_lines = tabulate(table1, headers=headers1, tablefmt="fancy_grid").splitlines()
    table2_lines = tabulate(table2, headers=headers2, tablefmt="fancy_grid").splitlines()

    max_width1 = max(len(line) for line in table1_lines)
    max_width2 = max(len(line) for line in table2_lines)

    title_line1 = title1.center(max_width1)
    title_line2 = title2.center(max_width2)

    max_lines = max(len(table1_lines), len(table2_lines)) + 1

    full_table1 = [title_line1] + table1_lines + [' ' * max_width1] * (max_lines - len(table1_lines) - 1)
    full_table2 = [title_line2] + table2_lines + [' ' * max_width2] * (max_lines - len(table2_lines) - 1)

    for line1, line2 in zip(full_table1, full_table2):
        print(line1.ljust(max_width1) + ' ' * padding + line2)

def choose_translation_language():
    LANGUAGES = {'ar': 'Arabic', 'nl': 'Dutch', 'en': 'English', 'fr': 'French', 'de': 'German', 'hi': 'Hindi', 'id': 'Indonesian', 'it': 'Italian', 'ja': 'Japanese', 'ko': 'Korean', 'pl': 'Polish', 'pt': 'Portuguese', 'ru': 'Russian', 'es': 'Spanish', 'sv': 'Swedish', 'tr': 'Turkish', 'uk': 'Ukrainian', 'vi': 'Vietnamese'}

    print("\nSelect target language for translation:")
    for code, lang in sorted(LANGUAGES.items()):
        print(f"{code} - {lang}")
    while True:
        lang_code = input("Language code (e.g. it, fr, es): ").strip().lower()
        if lang_code in LANGUAGES:
            return lang_code
        print("Invalid language code, try again.")

def extract_words_with_context(db_path, zipf_threshold=3.0, include_all=False):
    db_type = detect_kindle_db_type(db_path)
    words_table = 'words'
    lookups_table = 'lookups'

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT w.word, w.lang, l.usage
            FROM {lookups_table} l
            JOIN {words_table} w ON l.word_key = w.id
        """)
        data = cursor.fetchall()

    contexts = defaultdict(list)
    word_counts = defaultdict(int)
    word_langs = {}

    for word, lang, usage in data:
        if not word:
            continue
        word_lower = word.lower()
        contexts[word_lower].append(usage)
        word_counts[word_lower] += 1
        word_langs[word_lower] = lang or 'en'

    kept, discarded = [], []
    for word, count in word_counts.items():
        zipf = zipf_frequency(word, word_langs[word], wordlist='best')
        if include_all or count >= 2 or zipf >= zipf_threshold:
            kept.append((word, word_langs[word], zipf, contexts[word]))
        else:
            discarded.append((word, zipf, count))

    return kept, discarded

def print_stats(kept_words, discarded_words):
    print(f"\n\U0001F4C8 Words kept: {len(kept_words)}")
    kept_table = []
    for word, _, zipf, context_list in sorted(kept_words, key=lambda x: -x[2]):
        kept_table.append([word, f"{zipf:.2f}", len(context_list)])

    print(f"\n\U0001F6AB Words discarded: {len(discarded_words)}\n")
    discarded_table = []
    for word, zipf, count in sorted(discarded_words, key=lambda x: -x[1]):
        discarded_table.append([word, f"{zipf:.2f}", count])

    print_two_tables_side_by_side(
        kept_table, ['Word', 'Zipf', 'Contexts'],
        discarded_table, ['Word', 'Zipf', 'Count'],
        title1="Words kept",
        title2="Words discarded"
    )

def confirm_before_saving():
    while True:
        choice = input("\nDo you want to save these words and continue? [s] Save and continue / [e] Exit: ").strip().lower()
        if choice == 's':
            return True
        elif choice == 'e':
            return False
        else:
            print("❌ Invalid option. Type 's' to save and continue, or 'e' to exit.")

def add_or_update_word_with_contexts(conn, word, lang, new_contexts):
    word = word.lower()
    c = conn.cursor()
    c.execute("SELECT id FROM words WHERE word = ?", (word,))
    row = c.fetchone()

    unique_contexts = list(dict.fromkeys(new_contexts))
    new_added = False

    if row:
        word_id = row[0]
        c.execute("SELECT context FROM contexts WHERE word_id = ?", (word_id,))
        existing_contexts = set(ctx[0] for ctx in c.fetchall())
        contexts_to_add = [ctx for ctx in unique_contexts if ctx not in existing_contexts]
        for ctx in contexts_to_add:
            c.execute("INSERT OR IGNORE INTO contexts (word_id, context) VALUES (?, ?)", (word_id, ctx))
            new_added = True
    else:
        c.execute("INSERT INTO words (word, lang, translation, note_id) VALUES (?, ?, NULL, NULL)", (word, lang))
        word_id = c.lastrowid
        for ctx in unique_contexts:
            c.execute("INSERT INTO contexts (word_id, context) VALUES (?, ?)", (word_id, ctx))
        new_added = True

    conn.commit()
    return new_added

def update_vocab_db(dest_db_path, source_db_path, zipf_threshold=3.0, include_all=False):
    kept_words, discarded_words = extract_words_with_context(source_db_path, zipf_threshold, include_all)
    words_to_update = []

    with sqlite3.connect(dest_db_path) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE NOT NULL,
            lang TEXT NOT NULL,
            translation TEXT,
            note_id INTEGER
        );
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL,
            context TEXT NOT NULL,
            translation TEXT,
            UNIQUE(word_id, context),
            FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
        );
        """)
        conn.commit()

        for word, lang, zipf, contexts in tqdm(kept_words, desc="Updating vocab DB"):
            changed = add_or_update_word_with_contexts(conn, word, lang, contexts)
            if changed:
                words_to_update.append(word)

    return words_to_update

def generate_note_id(word):
    key = word.lower()
    return int(hashlib.sha1(key.encode('utf-8')).hexdigest()[:8], 16)


def translate_and_create_cards_from_db(db_path, target_lang, words_to_update=None):
    cards = []
    translator = GoogleTranslator(target=target_lang)

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        if words_to_update:
            placeholders = ",".join("?" for _ in words_to_update)
            c.execute(f"SELECT id, word, translation, note_id FROM words WHERE word IN ({placeholders})", tuple(words_to_update))
        else:
            c.execute("SELECT id, word, translation, note_id FROM words")
        words = c.fetchall()

        for word_id, word, translation, saved_note_id in tqdm(words, desc="Creating cards"):
            if not translation:
                try:
                    translation = translator.translate(word)
                    c.execute("UPDATE words SET translation = ? WHERE id = ?", (translation, word_id))
                    conn.commit()
                except Exception as e:
                    print(f"Error translating word '{word}': {e}")
                    translation = "?"

            c.execute("SELECT id, context, translation FROM contexts WHERE word_id = ?", (word_id,))
            rows = c.fetchall()

            contexts = []
            translations = []
            for ctx_id, context, ctx_translation in rows:
                if not ctx_translation:
                    try:
                        ctx_translation = translator.translate(context)
                        c.execute("UPDATE contexts SET translation = ? WHERE id = ?", (ctx_translation, ctx_id))
                        conn.commit()
                    except Exception as e:
                        print(f"Error translating context '{context}': {e}")
                        ctx_translation = "?"
                contexts.append(context)
                translations.append(ctx_translation)

                front = (
                    f"<div class='word-header'><b>{word}</b></div>" +
                    "".join([f"<div class='context-line'>{context.replace(word, f'<b>{word}</b>')}</div>" for context in contexts])
                )            
                back = "".join([f"<div class='translated-line'>{t}</div>" for t in translations]) + f"<div class='word-translation'>{translation}</div>"

            note_id = generate_note_id(word)
            if saved_note_id != note_id:
                c.execute("UPDATE words SET note_id = ? WHERE id = ?", (note_id, word_id))
                conn.commit()

            note = genanki.Note(
                model=model,
                fields=[front, back, word],
                guid=note_id
            )
            cards.append(note)

    return cards


def export_to_anki(cards, db_path, output_filename="Kindle_Vocab.apkg"):
    output_dir = os.path.dirname(os.path.abspath(db_path))
    output_path = os.path.join(output_dir, output_filename)

    deck = genanki.Deck(deck_id=2059400110, name='Kindle Vocabulary')
    for note in cards:
        deck.add_note(note)

    genanki.Package(deck).write_to_file(output_path)
    print(f"\n✅ Anki .apkg file saved to: {output_path}")

def main():
    dest_db_filename = "db_lexindle.db"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dest_db_path = os.path.join(script_dir, dest_db_filename)

    source_db_path = find_db_in_script_folder("vocab.db")
    if not source_db_path:
        print("❌ Kindle DB not found in the script folder. Exiting.")
        return

    while True:
        choice = input("Do you want all words (a) or filter by Zipf? [a/f] (default: f): ").strip().lower()
        if choice == 'a':
            include_all = True
            zipf_threshold = 0.0
            break
        elif choice == 'f' or choice == '':
            include_all = False
            print(
                "\nZipf frequency categories:\n"
                "Very rare: Zipf < 3\n"
                "Rare: 3 ≤ Zipf < 5\n"
                "Uncommon: 5 ≤ Zipf < 6\n"
                "Common: 6 ≤ Zipf < 7\n"
                "Very common: Zipf ≥ 7\n"
            )
            while True:
                try:
                    zipf_input = input("Zipf threshold between 0.0 and 10.0 (default: 3.0): ").strip()
                    zipf_threshold = float(zipf_input) if zipf_input else 3.0
                    if 0.0 <= zipf_threshold <= 10.0:
                        break
                    else:
                        print("❌ Please enter a number between 0.0 and 10.0.")
                except ValueError:
                    print("❌ Invalid number. Please enter a valid float (e.g., 3.0).")
            break
        else:
            print("❌ Invalid option. Use 'a' for all words or 'f' for filtering.")

    kept_words, discarded_words = extract_words_with_context(source_db_path, zipf_threshold, include_all)
    print_stats(kept_words, discarded_words)

    if not confirm_before_saving():
        print("❎ Exiting without saving.")
        return

    words_to_update = update_vocab_db(dest_db_path, source_db_path, zipf_threshold, include_all)
    target_lang = choose_translation_language()
    cards = translate_and_create_cards_from_db(dest_db_path, target_lang, words_to_update)
    export_to_anki(cards, dest_db_path)

if __name__ == "__main__":
    main()