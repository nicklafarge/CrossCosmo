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