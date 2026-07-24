/**
 * Qismat Takeaway — Main JavaScript
 * Handles: mobile nav, cart interactions, favourites, reviews, extras pricing, etc.
 */

document.addEventListener('DOMContentLoaded', () => {

    // ──────── Mobile Nav Toggle ────────
    const navToggle = document.getElementById('navToggle');
    const mainNav = document.getElementById('mainNav');

    if (navToggle && mainNav) {
        navToggle.addEventListener('click', () => {
            mainNav.classList.toggle('open');
        });

        // Close nav when clicking a link (mobile)
        mainNav.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                mainNav.classList.remove('open');
            });
        });
    }

    // ──────── Cart: Quantity increment/decrement ────────
    document.querySelectorAll('.qty-update-form .qty-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            // These forms submit via the inline onclick, but we let that work
            // This is just for additional safety
        });
    });

    // ──────── Cart: Remove item confirmation ────────
    document.querySelectorAll('.btn-remove').forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Remove this item from your cart?')) {
                e.preventDefault();
            }
        });
    });

    // ──────── AJAX Cart: Quick Add from menu cards ────────
    document.querySelectorAll('.quick-add-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            // Allow normal POST submission
        });
    });

    // ──────── Product Page: Extras price calculation ────────
    // This is already handled inline in menu_item_detail.html via the extra JS block

    // ──────── Favourite Toggle (AJAX) ────────
    document.querySelectorAll('.favourite-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const btn = this.querySelector('.btn-favourite');

            try {
                const response = await fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                });

                const data = await response.json();

                if (data.success) {
                    if (data.is_favourite) {
                        btn.textContent = '❤️';
                        btn.classList.add('active');
                    } else {
                        btn.textContent = '🤍';
                        btn.classList.remove('active');
                    }
                    // Show a brief notification
                    showNotification(data.message);
                }
            } catch (error) {
                console.error('Favourite toggle failed:', error);
            }
        });
    });

    // ──────── Coupon: Apply via AJAX ────────
    const couponForm = document.querySelector('.coupon-form');
    if (couponForm) {
        couponForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);

            try {
                const response = await fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                });

                const data = await response.json();

                if (data.success) {
                    showNotification(data.message, 'success');
                    // Reload page to reflect updated cart
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification(data.message, 'error');
                }
            } catch (error) {
                console.error('Coupon apply failed:', error);
            }
        });
    }

    // ──────── Coupon: Remove via AJAX ────────
    const removeCouponBtn = document.querySelector('.btn-remove-coupon');
    if (removeCouponBtn) {
        removeCouponBtn.addEventListener('click', async function(e) {
            e.preventDefault();

            const form = this.closest('form');

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: new FormData(form),
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                });

                const data = await response.json();

                if (data.success) {
                    showNotification(data.message, 'success');
                    setTimeout(() => location.reload(), 1000);
                }
            } catch (error) {
                console.error('Coupon remove failed:', error);
            }
        });
    }

    // ──────── Review Star Rating Interaction ────────
    document.querySelectorAll('.stars-input label').forEach(label => {
        label.addEventListener('mouseenter', function() {
            const siblings = this.closest('.stars-input').querySelectorAll('label');
            let highlight = false;
            siblings.forEach(s => {
                if (s === this) highlight = true;
                s.style.color = highlight ? '#f59e0b' : '#ddd';
            });
        });

        label.addEventListener('mouseleave', function() {
            const container = this.closest('.stars-input');
            const checked = container.querySelector('input:checked');
            container.querySelectorAll('label').forEach(s => {
                s.style.color = '#ddd';
            });
            if (checked) {
                let checkedNext = false;
                container.querySelectorAll('label').forEach(s => {
                    if (s.getAttribute('for') === checked.id) checkedNext = true;
                    if (checkedNext) s.style.color = '#f59e0b';
                });
            }
        });
    });

    // ──────── Order Tracking: Auto-refresh ────────
    // Already handled inline in order_tracking.html

    // ──────── Toastr Notification System ────────
    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            danger: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle',
        };

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('data-toast', '');
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon"><i class="fas ${icons[type] || icons.info}"></i></span>
                <span class="toast-message">${message}</span>
            </div>
            <button class="toast-close" data-toast-close>&times;</button>
        `;
        container.appendChild(toast);

        // Trigger slide-in
        requestAnimationFrame(() => toast.classList.add('toast-visible'));

        // Auto-dismiss after 3 seconds
        const dismissTimer = setTimeout(() => dismissToast(toast), 3000);

        // Manual close
        toast.querySelector('[data-toast-close]').addEventListener('click', () => {
            clearTimeout(dismissTimer);
            dismissToast(toast);
        });
    }

    function dismissToast(toast) {
        if (toast.classList.contains('toast-dismissing')) return;
        toast.classList.add('toast-dismissing');
        toast.classList.remove('toast-visible');
        setTimeout(() => toast.remove(), 300);
    }

    // Auto-dismiss existing server-rendered toasts
    document.querySelectorAll('[data-toast]').forEach(toast => {
        setTimeout(() => dismissToast(toast), 3000);

        toast.querySelector('[data-toast-close]')?.addEventListener('click', () => {
            dismissToast(toast);
        });
    });

    // ──────── Backward-compatible alias ────────
    function showNotification(message, type = 'info') {
        showToast(message, type);
    }

    // ──────── Clear Cart Confirmation ────────
    const clearCartForm = document.querySelector('.cart-actions-top form');
    if (clearCartForm) {
        clearCartForm.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to clear your entire cart?')) {
                e.preventDefault();
            }
        });
    }

    // ──────── Cancel Order Confirmation ────────
    // Handled inline with onsubmit confirm

    // ──────── Staff Panel: Sidebar Toggle ────────
    const staffMobileToggle = document.getElementById('staffMobileToggle');
    const staffSidebarToggle = document.getElementById('staffSidebarToggle');
    const staffSidebar = document.getElementById('staffSidebar');

    function toggleStaffSidebar() {
        if (staffSidebar) {
            staffSidebar.classList.toggle('open');
        }
    }

    if (staffMobileToggle) {
        staffMobileToggle.addEventListener('click', toggleStaffSidebar);
    }

    if (staffSidebarToggle) {
        staffSidebarToggle.addEventListener('click', toggleStaffSidebar);
    }

    // Close sidebar when clicking outside on mobile
    if (staffSidebar) {
        document.addEventListener('click', function(e) {
            const isMobile = window.innerWidth <= 768;
            if (isMobile && staffSidebar.classList.contains('open')) {
                if (!staffSidebar.contains(e.target) &&
                    !staffMobileToggle?.contains(e.target) &&
                    !staffSidebarToggle?.contains(e.target)) {
                    staffSidebar.classList.remove('open');
                }
            }
        });
    }

    console.log('Qismat Takeaway — JS loaded');
});

