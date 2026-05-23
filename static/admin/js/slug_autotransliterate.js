/**
 * Auto-transliterate Cyrillic name field to slug field in Django admin.
 * Converts Russian characters to English equivalents in real-time.
 */

(function() {
    'use strict';

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

    function slugify(text) {
        let result = '';
        for (let char of text) {
            result += translitMap[char] || char;
        }
        result = result.toLowerCase();
        result = result.replace(/\s+/g, '-');
        result = result.replace(/[^a-z0-9-]/g, '');
        result = result.replace(/-+/g, '-');
        result = result.replace(/^-|-$/g, '');
        return result;
    }

    document.addEventListener('DOMContentLoaded', function() {
        const nameInput = document.getElementById('id_name');
        const slugInput = document.getElementById('id_slug');

        if (!nameInput || !slugInput) return;

        // If slug already has a value, it's an edit — don't auto-update
        const isEdit = slugInput.value !== '';

        let manualEdit = false;

        slugInput.addEventListener('focus', function() {
            manualEdit = true;
        });

        nameInput.addEventListener('input', function() {
            if (manualEdit) return;
            if (isEdit) return; // preserve existing slug on edit

            const name = this.value.trim();
            slugInput.value = name ? slugify(name) : '';
        });
    });
})();
