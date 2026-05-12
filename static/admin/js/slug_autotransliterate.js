/**
 * Auto-transliterate Cyrillic name field to slug field in Django admin.
 * Converts Russian characters to English equivalents in real-time.
 */

(function() {
    'use strict';

    // Russian to English transliteration mapping
    const translitMap = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
        'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
        'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch',
        'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
        'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    };

    // Slugify the result: lowercase, replace spaces with hyphens, remove non-alphanum
    function slugify(text) {
        let result = '';
        for (let char of text) {
            result += translitMap[char] || char;
        }
        result = result.toLowerCase();
        result = result.replace(/\s+/g, '-');          // spaces → hyphens
        result = result.replace(/[^a-z0-9-]/g, '');    // keep only alphanum + hyphens
        result = result.replace(/-+/g, '-');           // collapse multiple hyphens
        result = result.replace(/^-|-$/g, '');         // trim hyphens
        return result;
    }

    document.addEventListener('DOMContentLoaded', function() {
        const nameInput = document.getElementById('id_name');
        const slugInput = document.getElementById('id_slug');

        if (!nameInput || !slugInput) return;

        // Only auto-generate if slug is empty or prepopulated_fields is active
        const shouldAutoGenerate = function() {
            return slugInput.value === '' || slugInput.hasAttribute('readonly');
        };

        nameInput.addEventListener('input', function() {
            if (shouldAutoGenerate()) {
                const name = this.value.trim();
                if (name) {
                    slugInput.value = slugify(name);
                } else {
                    slugInput.value = '';
                }
            }
        });

        // Also replace slug if user manually edits and then focuses back on name
        slugInput.addEventListener('focus', function() {
            // Mark that user is manually editing — stop auto-generation
            this.dataset.manualEdit = 'true';
        });

        nameInput.addEventListener('input', function() {
            // If user started manual edit on slug, don't override it
            if (slugInput.dataset.manualEdit === 'true') {
                return;
            }
            if (shouldAutoGenerate()) {
                const name = this.value.trim();
                slugInput.value = name ? slugify(name) : '';
            }
        });
    });
})();
