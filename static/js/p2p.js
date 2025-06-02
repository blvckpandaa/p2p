/**
 * P2P Exchange JavaScript
 * Обработка форм и AJAX-запросов для P2P-биржи
 */

document.addEventListener('DOMContentLoaded', function() {
    // Обработка форм создания ордеров
    const p2pForms = document.querySelectorAll('.p2p-form');
    
    p2pForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Показываем индикатор загрузки
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.textContent = 'Обработка...';
            submitButton.disabled = true;
            
            // Собираем данные формы
            const formData = new FormData(form);
            
            // Отправляем AJAX-запрос
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                // Обрабатываем ответ
                if (data.status === 'success') {
                    showNotification(data.message, 'success');
                    
                    // Если это создание ордера, очищаем форму
                    if (form.action.includes('create_order')) {
                        form.reset();
                    }
                    
                    // Если есть редирект, переходим по указанному URL
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    } else {
                        // Если нет редиректа, обновляем страницу через 1 секунду
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    }
                } else {
                    showNotification(data.message, 'error');
                    submitButton.textContent = originalText;
                    submitButton.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Произошла ошибка при обработке запроса', 'error');
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            });
        });
    });
    
    // Функции фильтрации и сортировки ордеров
    setupFilters();
});

/**
 * Показывает уведомление пользователю
 * @param {string} message - текст сообщения
 * @param {string} type - тип уведомления (success, error)
 */
function showNotification(message, type = 'info') {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <div class="notification-message">${message}</div>
            <button class="notification-close">&times;</button>
        </div>
    `;
    
    // Добавляем на страницу
    document.body.appendChild(notification);
    
    // Анимация появления
    setTimeout(() => {
        notification.classList.add('notification-show');
    }, 10);
    
    // Закрытие по клику на крестик
    const closeButton = notification.querySelector('.notification-close');
    closeButton.addEventListener('click', () => {
        closeNotification(notification);
    });
    
    // Автоматическое закрытие через 5 секунд
    setTimeout(() => {
        closeNotification(notification);
    }, 5000);
}

/**
 * Закрывает уведомление
 * @param {HTMLElement} notification - элемент уведомления
 */
function closeNotification(notification) {
    notification.classList.remove('notification-show');
    notification.classList.add('notification-hide');
    
    // Удаляем элемент после завершения анимации
    setTimeout(() => {
        notification.remove();
    }, 300);
}

/**
 * Настраивает фильтры и сортировку ордеров
 */
function setupFilters() {
    // Получаем элементы фильтрации
    const filterPrice = document.getElementById('filter-price');
    const filterAmount = document.getElementById('filter-amount');
    const sortSelect = document.getElementById('sort-orders');
    
    // Если элементы существуют, добавляем обработчики событий
    if (filterPrice) {
        filterPrice.addEventListener('input', filterOrders);
    }
    
    if (filterAmount) {
        filterAmount.addEventListener('input', filterOrders);
    }
    
    if (sortSelect) {
        sortSelect.addEventListener('change', sortOrders);
    }
}

/**
 * Фильтрует ордера по заданным критериям
 */
function filterOrders() {
    const filterPrice = document.getElementById('filter-price').value;
    const filterAmount = document.getElementById('filter-amount').value;
    const orderCards = document.querySelectorAll('.order-card');
    
    orderCards.forEach(card => {
        const price = parseFloat(card.dataset.price || 0);
        const amount = parseFloat(card.dataset.amount || 0);
        let visible = true;
        
        if (filterPrice && price > filterPrice) {
            visible = false;
        }
        
        if (filterAmount && amount < filterAmount) {
            visible = false;
        }
        
        if (visible) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

/**
 * Сортирует ордера по выбранному критерию
 */
function sortOrders() {
    const sortSelect = document.getElementById('sort-orders');
    const sortValue = sortSelect.value;
    const ordersList = document.querySelector('.orders-list');
    const orderCards = Array.from(document.querySelectorAll('.order-card'));
    
    // Сортируем элементы
    orderCards.sort((a, b) => {
        const aValue = parseFloat(a.dataset[sortValue] || 0);
        const bValue = parseFloat(b.dataset[sortValue] || 0);
        
        if (sortValue === 'price') {
            return aValue - bValue; // По возрастанию цены
        } else if (sortValue === 'amount') {
            return bValue - aValue; // По убыванию количества
        } else if (sortValue === 'date') {
            return parseInt(a.dataset.timestamp || 0) - parseInt(b.dataset.timestamp || 0); // По дате создания
        }
        
        return 0;
    });
    
    // Удаляем и добавляем элементы в новом порядке
    orderCards.forEach(card => {
        ordersList.appendChild(card);
    });
} 