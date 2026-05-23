/**
 * booking.js — JavaScript for booking form
 * Handles phone mask, price calculation, and form interactions
 */

'use strict';

/* =========================================================
   Phone number mask
   ========================================================= */
class PhoneMask {
    constructor(input) {
        this.input = input;
        this.mask = '+7 (000) 000-00-00';
        this.placeholder = '_';
        this.init();
    }

    init() {
        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('focus', (e) => this.handleFocus(e));
        this.input.addEventListener('blur', (e) => this.handleBlur(e));
    }

    handleInput(e) {
        const value = e.target.value;
        const cleaned = this.cleanValue(value);
        const formatted = this.formatValue(cleaned);
        
        if (formatted !== value) {
            const cursorPos = this.getCursorPosition(value, formatted, e.target.selectionStart);
            e.target.value = formatted;
            e.target.setSelectionRange(cursorPos, cursorPos);
        }
    }

    handleKeydown(e) {
        // Allow backspace, delete, tab, escape, enter
        if ([8, 9, 27, 13, 46].indexOf(e.keyCode) !== -1 ||
            // Allow Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
            (e.keyCode === 65 && e.ctrlKey === true) ||
            (e.keyCode === 67 && e.ctrlKey === true) ||
            (e.keyCode === 86 && e.ctrlKey === true) ||
            (e.keyCode === 88 && e.ctrlKey === true)) {
            return;
        }
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    }

    handleFocus(e) {
        if (!e.target.value || e.target.value === '+7 (___) ___-__-__') {
            e.target.value = '+7 (';
            e.target.setSelectionRange(4, 4);
        }
    }

    handleBlur(e) {
        if (e.target.value === '+7 (' || e.target.value === '+7 (___) ___-__-__') {
            e.target.value = '';
        }
    }

    cleanValue(value) {
        return value.replace(/\D/g, '').substring(1); // Remove +7 and non-digits
    }

    formatValue(cleaned) {
        if (!cleaned) return '';
        
        let formatted = '+7 (';
        
        if (cleaned.length > 0) {
            formatted += cleaned.substring(0, 3);
        }
        
        if (cleaned.length >= 4) {
            formatted += ') ' + cleaned.substring(3, 6);
        } else if (cleaned.length > 0) {
            formatted += ')';
        }
        
        if (cleaned.length >= 7) {
            formatted += '-' + cleaned.substring(6, 8);
        }
        
        if (cleaned.length >= 9) {
            formatted += '-' + cleaned.substring(8, 10);
        }
        
        return formatted;
    }

    getCursorPosition(oldValue, newValue, oldPos) {
        // Simple cursor position calculation
        return Math.min(oldPos + (newValue.length - oldValue.length), newValue.length);
    }
}

/* =========================================================
   Price Calculator
   ========================================================= */
class BookingPriceCalculator {
    constructor() {
        this.categorySelect  = document.getElementById('id_room_category');
        this.checkInInput    = document.getElementById('id_check_in');
        this.checkOutInput   = document.getElementById('id_check_out');
        this.adultsInput     = document.getElementById('id_adults');
        this.childrenInput   = document.getElementById('id_children');
        this.earlyCheckinBox = document.getElementById('id_early_check_in');

        this.previewElements = {
            categoryName:  document.getElementById('previewCategoryName'),
            dates:         document.getElementById('previewDatesValue'),
            nights:        document.getElementById('previewNights'),
            pricePerNight: document.getElementById('previewPricePerNight'),
            earlyRow:      document.getElementById('earlyCheckinRow'),
            earlyVal:      document.getElementById('previewEarlyCheckin'),
            total:         document.getElementById('previewTotal'),
        };

        this.submitBtn = document.getElementById('submitBtn');
        this.init();
    }

    init() {
        if (!this.categorySelect || !this.checkInInput || !this.checkOutInput) return;

        const recalc = () => this.updatePreview();
        this.categorySelect.addEventListener('change', recalc);
        this.checkInInput.addEventListener('change', recalc);
        this.checkOutInput.addEventListener('change', recalc);
        this.adultsInput?.addEventListener('change', recalc);
        this.adultsInput?.addEventListener('input', recalc);
        this.childrenInput?.addEventListener('change', recalc);
        this.childrenInput?.addEventListener('input', recalc);
        // Listen for early check-in changes via custom event (hidden input doesn't fire 'change')
        document.addEventListener('earlyCheckinChanged', recalc);
        // Listen for bed_sharing changes
        document.querySelectorAll('input[name="bed_sharing"]').forEach(r =>
            r.addEventListener('change', recalc)
        );

        this.setMinimumDates();
        this.updatePreview();
    }

    setMinimumDates() {
        const today = new Date().toISOString().split('T')[0];
        this.checkInInput.min = today;
        
        this.checkInInput.addEventListener('change', () => {
            const checkInDate = new Date(this.checkInInput.value);
            checkInDate.setDate(checkInDate.getDate() + 1);
            this.checkOutInput.min = checkInDate.toISOString().split('T')[0];
            
            // If check-out is before new minimum, update it
            if (this.checkOutInput.value && new Date(this.checkOutInput.value) <= new Date(this.checkInInput.value)) {
                this.checkOutInput.value = checkInDate.toISOString().split('T')[0];
            }
        });
    }

    async updatePreview() {
        const categoryId   = this.categorySelect.value;
        const checkIn      = this.checkInInput.value;
        const checkOut     = this.checkOutInput.value;
        const adults       = this.adultsInput?.value || 1;
        const children     = this.childrenInput?.value || 0;
        const earlyCheckin = document.getElementById('id_early_check_in')?.value === 'on' ? 'true' : 'false';
        // Derive occupancy_type from adults + children + bed_sharing
        const bedSharing   = document.querySelector('input[name="bed_sharing"]:checked')?.value || 'two_beds';
        const totalPaid    = parseInt(adults) + parseInt(children);
        let occupancy = 'solo';
        if (totalPaid === 2) {
            occupancy = bedSharing === 'one_bed' ? 'newlyweds' : 'two_guests';
        } else if (totalPaid > 2) {
            occupancy = 'two_guests';
        }

        this.resetPreview();

        if (!categoryId || !checkIn || !checkOut) {
            this.disableSubmit('Выберите категорию и даты');
            return;
        }

        if (new Date(checkOut) <= new Date(checkIn)) {
            this.showError('Дата выезда должна быть позже даты заезда');
            return;
        }

        try {
            this.showLoading();

            const url = `/bookings/calculate-prices/?check_in=${checkIn}&check_out=${checkOut}`
                + `&adults=${adults}&children=${children}`
                + `&occupancy_type=${occupancy}&early_check_in=${earlyCheckin}`;

            const response = await fetch(url);
            const data = await response.json();

            if (!response.ok) throw new Error(data.error || 'Ошибка расчёта цен');

            const categoryPrice = data.prices[categoryId];
            if (!categoryPrice) throw new Error('Цена для выбранной категории не найдена');
            if (categoryPrice.error) throw new Error(categoryPrice.error);

            this.updatePreviewDisplay(categoryPrice, checkIn, checkOut, earlyCheckin === 'true');
            this.enableSubmit();

        } catch (error) {
            console.error('Price calculation error:', error);
            this.showError(error.message);
        }
    }

    updatePreviewDisplay(priceData, checkIn, checkOut, earlyCheckin) {
        const categoryName = this.categorySelect.options[this.categorySelect.selectedIndex].text;
        const checkInFmt   = new Date(checkIn).toLocaleDateString('ru-RU');
        const checkOutFmt  = new Date(checkOut).toLocaleDateString('ru-RU');

        if (this.previewElements.categoryName)
            this.previewElements.categoryName.textContent = categoryName;

        // Guests summary
        const guestsEl = document.getElementById('previewGuestsValue');
        if (guestsEl) {
            const adults   = parseInt(this.adultsInput?.value || 1);
            const children = parseInt(this.childrenInput?.value || 0);
            let txt = `${adults} взр.`;
            if (children > 0) txt += `, ${children} дет. со спальным местом`;
            guestsEl.textContent = txt;
        }

        if (this.previewElements.dates)
            this.previewElements.dates.textContent = `${checkInFmt} — ${checkOutFmt}`;

        if (this.previewElements.nights)
            this.previewElements.nights.textContent =
                `${priceData.nights} ${this.getNightsWord(priceData.nights)}`;

        if (this.previewElements.pricePerNight)
            this.previewElements.pricePerNight.textContent =
                `${this.formatPrice(priceData.price_per_night)} ₽`;

        // Early check-in row
        const earlyRow = this.previewElements.earlyRow;
        const earlyVal = this.previewElements.earlyVal;
        if (earlyRow) {
            if (earlyCheckin && priceData.early_checkin_surcharge > 0) {
                earlyRow.style.display = 'flex';
                if (earlyVal)
                    earlyVal.textContent = `+${this.formatPrice(priceData.early_checkin_surcharge)} ₽`;
            } else {
                earlyRow.style.display = 'none';
            }
        }

        if (this.previewElements.total)
            this.previewElements.total.textContent =
                `${this.formatPrice(priceData.final_total || priceData.total_price)} ₽`;
    }

    resetPreview() {
        ['categoryName', 'dates', 'nights', 'pricePerNight', 'earlyVal', 'total'].forEach(key => {
            const el = this.previewElements[key];
            if (el) el.textContent = '—';
        });
        if (this.previewElements.earlyRow) {
            this.previewElements.earlyRow.style.display = 'none';
        }
        const guestsEl = document.getElementById('previewGuestsValue');
        if (guestsEl) guestsEl.textContent = '—';
    }

    showLoading() {
        if (this.previewElements.total) {
            this.previewElements.total.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Расчет...';
        }
    }

    showError(message) {
        if (this.previewElements.total) {
            this.previewElements.total.textContent = 'Ошибка расчета';
            this.previewElements.total.style.color = '#dc3545';
        }
        this.disableSubmit(message);
    }

    enableSubmit() {
        if (this.submitBtn) {
            this.submitBtn.disabled = false;
            this.submitBtn.title = '';
        }
        if (this.previewElements.total) {
            this.previewElements.total.style.color = '';
        }
    }

    disableSubmit(reason) {
        if (this.submitBtn) {
            this.submitBtn.disabled = true;
            this.submitBtn.title = reason;
        }
    }

    formatPrice(price) {
        return new Intl.NumberFormat('ru-RU').format(Math.round(price));
    }

    getNightsWord(count) {
        if (count % 10 === 1 && count % 100 !== 11) return 'ночь';
        if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) return 'ночи';
        return 'ночей';
    }
}

/* =========================================================
   Initialize on DOM ready
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize phone mask for all phone inputs
    document.querySelectorAll('input[type="tel"], input[data-mask]').forEach(input => {
        if (input.dataset.mask && input.dataset.mask.includes('+7')) {
            new PhoneMask(input);
        }
    });

    // Initialize price calculator
    new BookingPriceCalculator();
});