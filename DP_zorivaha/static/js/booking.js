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
        this.categorySelect = document.getElementById('id_room_category');
        this.checkInInput = document.getElementById('id_check_in');
        this.checkOutInput = document.getElementById('id_check_out');
        this.adultsInput = document.getElementById('id_adults');
        this.childrenInput = document.getElementById('id_children');
        
        this.previewElements = {
            categoryName: document.getElementById('previewCategoryName'),
            dates: document.getElementById('previewDatesValue'),
            nights: document.getElementById('previewNights'),
            pricePerNight: document.getElementById('previewPricePerNight'),
            total: document.getElementById('previewTotal')
        };
        
        this.submitBtn = document.getElementById('submitBtn');
        this.init();
    }

    init() {
        if (!this.categorySelect || !this.checkInInput || !this.checkOutInput) {
            return; // Not on booking form page
        }

        // Bind events
        this.categorySelect.addEventListener('change', () => this.updatePreview());
        this.checkInInput.addEventListener('change', () => this.updatePreview());
        this.checkOutInput.addEventListener('change', () => this.updatePreview());
        this.adultsInput?.addEventListener('change', () => this.updatePreview());
        this.childrenInput?.addEventListener('change', () => this.updatePreview());

        // Set minimum dates
        this.setMinimumDates();
        
        // Initial calculation
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
        const categoryId = this.categorySelect.value;
        const checkIn = this.checkInInput.value;
        const checkOut = this.checkOutInput.value;
        const adults = this.adultsInput?.value || 1;
        const children = this.childrenInput?.value || 0;

        // Reset preview
        this.resetPreview();

        if (!categoryId || !checkIn || !checkOut) {
            this.disableSubmit('Выберите категорию и даты');
            return;
        }

        // Validate dates
        if (new Date(checkOut) <= new Date(checkIn)) {
            this.showError('Дата выезда должна быть позже даты заезда');
            return;
        }

        try {
            this.showLoading();
            
            const response = await fetch(`/bookings/calculate-prices/?check_in=${checkIn}&check_out=${checkOut}&adults=${adults}&children=${children}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Ошибка расчета цен');
            }

            const categoryPrice = data.prices[categoryId];
            if (!categoryPrice) {
                throw new Error('Цена для выбранной категории не найдена');
            }

            if (categoryPrice.error) {
                throw new Error(categoryPrice.error);
            }

            this.updatePreviewDisplay(categoryPrice, checkIn, checkOut);
            this.enableSubmit();

        } catch (error) {
            console.error('Price calculation error:', error);
            this.showError(error.message);
        }
    }

    updatePreviewDisplay(priceData, checkIn, checkOut) {
        const categoryName = this.categorySelect.options[this.categorySelect.selectedIndex].text;
        
        // Format dates
        const checkInFormatted = new Date(checkIn).toLocaleDateString('ru-RU');
        const checkOutFormatted = new Date(checkOut).toLocaleDateString('ru-RU');
        
        // Update preview elements
        if (this.previewElements.categoryName) {
            this.previewElements.categoryName.textContent = categoryName;
        }
        
        if (this.previewElements.dates) {
            this.previewElements.dates.textContent = `${checkInFormatted} — ${checkOutFormatted}`;
        }
        
        if (this.previewElements.nights) {
            this.previewElements.nights.textContent = `${priceData.nights} ${this.getNightsWord(priceData.nights)}`;
        }
        
        if (this.previewElements.pricePerNight) {
            this.previewElements.pricePerNight.textContent = `${this.formatPrice(priceData.price_per_night)} ₽`;
        }
        
        if (this.previewElements.total) {
            let totalText = `${this.formatPrice(priceData.total_price)} ₽`;
            if (priceData.discount_amount > 0) {
                totalText += ` (скидка: ${this.formatPrice(priceData.discount_amount)} ₽)`;
            }
            this.previewElements.total.textContent = totalText;
        }

        // Show occupancy info if applicable
        if (priceData.occupancy_multiplier !== 1.0) {
            const multiplierText = priceData.occupancy_multiplier > 1.0 ? 
                `Высокий спрос (+${Math.round((priceData.occupancy_multiplier - 1) * 100)}%)` :
                `Низкий спрос (${Math.round((1 - priceData.occupancy_multiplier) * 100)}% скидка)`;
            
            // You can add this info somewhere in the UI
            console.log('Occupancy info:', multiplierText);
        }
    }

    resetPreview() {
        Object.values(this.previewElements).forEach(el => {
            if (el) el.textContent = '—';
        });
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