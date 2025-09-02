"""Crosserville built-in word list

Stored in browser cookie


Download script:
```
// Extract Words database as CSV
(async function() {
    const request = indexedDB.open('Words');
    request.onsuccess = function(event) {
        const db = event.target.result;
        const transaction = db.transaction(['wordLists'], 'readonly');
        const objectStore = transaction.objectStore('wordLists');
        const getRequest = objectStore.get(1);
        
        getRequest.onsuccess = function(event) {
            const data = event.target.result;
            if (data) {
                const allRows = [];
                for (const [key, arrays] of Object.entries(data)) {
                    if (Array.isArray(arrays)) {
                        arrays.forEach(item => {
                            allRows.push({
                                mapKey: key,
                                n: item.n,
                                r: item.r,
                                s: item.s,
                                w: item.w
                            });
                        });
                    }
                }
                
                // Create CSV
                let csv = 'mapKey,n,r,s,w\n';
                allRows.forEach(row => {
                    csv += `${row.mapKey},"${row.n}","${row.r}","${row.s}","${row.w}"\n`;
                });
                
                const blob = new Blob([csv], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'wordLists_data.csv';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                console.log(`Downloaded ${allRows.length} rows from Words database`);
            }
        };
    };
})();

// Extract NYTWords database (word list)
(async function() {
    const request = indexedDB.open('NYTWords');
    request.onsuccess = function(event) {
        const db = event.target.result;
        const transaction = db.transaction(['words'], 'readonly');
        const objectStore = transaction.objectStore('words');
        const getRequest = objectStore.get('wordList');
        
        getRequest.onsuccess = function(event) {
            const wordArray = event.target.result;
            if (wordArray && Array.isArray(wordArray)) {
                // Save as text file with one word per line
                const textStr = wordArray.join('\n');
                const blob = new Blob([textStr], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'nyt_wordlist.txt';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                console.log(`Downloaded ${wordArray.length} words from NYTWords database`);
            }
        };
    };
})();
```
"""

import logging

import polars as pl
from pony import orm

from crosscosmos.config import project_root

logger = logging.getLogger(__name__)

crosserville_word_list_path = project_root / "resources" / "word_lists" / "crosserville_list.csv"
crosserville_word_list_db_path = project_root / "word_dbs" / "crosserville_words.sqlite"

crosserville_word_list_word_db = orm.Database()
crosserville_word_list_word_db.bind(
    provider="sqlite",
    filename=str(crosserville_word_list_db_path),
    create_db=True,
)


class CrosservilleWord(crosserville_word_list_word_db.Entity):
    word = orm.PrimaryKey(str)
    score = orm.Required(int)
    count = orm.Required(int)


crosserville_word_list_word_db.generate_mapping(create_tables=True)



def read_dataframe() -> pl.DataFrame:
    df = pl.read_csv(crosserville_word_list_path, columns=["n", "s", "w"])
    df = df.rename({"w": "word", "n": "count"})

    s_min = df["s"].min()
    s_max = df["s"].max()
    s_span = s_max - s_min
    df = df.with_columns(
        score=((pl.col("s")-s_min)/s_span*100).round()
    )
    df= df.drop("s")
    return df

def save_crosserville_database():
    db_uri = f"sqlite:///{crosserville_word_list_db_path}"
    df = read_dataframe()
    df.write_database(
        table_name="CrosservilleWord",
        connection=db_uri,
        if_table_exists="append"
    )


if __name__ == "__main__":
    save_crosserville_database()
