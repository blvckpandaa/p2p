// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Установка темы в соответствии с Telegram
document.addEventListener('DOMContentLoaded', function() {
    // Применение темы Telegram
    if (tg.colorScheme === 'dark') {
        document.body.classList.add('dark-theme');
        document.documentElement.style.setProperty('--text', '#FFFFFF');
    } else {
        document.body.classList.add('light-theme');
        document.documentElement.style.setProperty('--text', '#0D1F4A');
    }
    
    // Инициализация анимации полива
    initWateringAnimation();
    
    // Инициализация обработчиков для P2P форм
    initP2PForms();
    
    // Инициализация модальных окон
    initModals();
});

// Функция для создания эффекта полива деревьев
function initWateringAnimation() {
    const waterButtons = document.querySelectorAll('.water-button');
    
    waterButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const treeContainer = this.closest('.card').querySelector('.tree-container');
            
            // Создаем капли воды
            for (let i = 0; i < 5; i++) {
                setTimeout(() => {
                    const droplet = document.createElement('div');
                    droplet.classList.add('water-droplet');
                    
                    // Случайное положение капли
                    const randomLeft = Math.floor(Math.random() * 80) + 10; // 10% - 90%
                    droplet.style.left = `${randomLeft}%`;
                    
                    // Добавляем каплю в контейнер дерева
                    treeContainer.appendChild(droplet);
                    
                    // Удаляем каплю после завершения анимации
                    setTimeout(() => {
                        droplet.remove();
                    }, 2000);
                }, i * 200);
            }
            
            // Отправляем запрос на сервер
            const treeId = this.dataset.treeId;
            fetch(`/tree/${treeId}/water/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Обновляем интерфейс при успешном поливе
                    const infoElement = this.closest('.card').querySelector('.tree-info');
                    if (infoElement) {
                        infoElement.textContent = `Полив успешен! +${data.reward} токенов`;
                        infoElement.classList.add('text-accent', 'animate-pulse');
                        
                        setTimeout(() => {
                            infoElement.classList.remove('animate-pulse');
                        }, 3000);
                    }
                }
            })
            .catch(error => {
                console.error('Ошибка при поливе:', error);
            });
        });
    });
}

// Инициализация форм для P2P обмена
function initP2PForms() {
    const p2pForms = document.querySelectorAll('.p2p-form');
    
    p2pForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const action = this.getAttribute('action');
            
            fetch(action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Показываем уведомление об успехе
                    showNotification(data.message, 'success');
                    
                    // Обновляем страницу через 2 секунды
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    // Показываем уведомление об ошибке
                    showNotification(data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Ошибка при отправке формы:', error);
                showNotification('Произошла ошибка при обработке запроса', 'error');
            });
        });
    });
}

// Инициализация модальных окон
function initModals() {
    const modalTriggers = document.querySelectorAll('[data-modal]');
    const modals = document.querySelectorAll('.modal');
    
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            
            const modalId = this.dataset.modal;
            const modal = document.getElementById(modalId);
            
            if (modal) {
                modal.classList.remove('hidden');
                document.body.classList.add('overflow-hidden');
            }
        });
    });
    
    // Закрытие модальных окон
    document.querySelectorAll('.modal-close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            modal.classList.add('hidden');
            document.body.classList.remove('overflow-hidden');
        });
    });
    
    // Закрытие по клику на оверлей
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.add('hidden');
                document.body.classList.remove('overflow-hidden');
            }
        });
    });
}

// Показать уведомление
function showNotification(message, type = 'info') {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.classList.add('notification', `notification-${type}`);
    notification.textContent = message;
    
    // Добавляем в DOM
    document.body.appendChild(notification);
    
    // Анимация появления
    setTimeout(() => {
        notification.classList.add('notification-show');
    }, 10);
    
    // Удаляем через 3 секунды
    setTimeout(() => {
        notification.classList.remove('notification-show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Получение CSRF токена из cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Функция для создания анимации роста дерева
function animateTreeGrowth(treeElement) {
    treeElement.style.transform = 'scale(0.8)';
    treeElement.style.opacity = '0.5';
    
    setTimeout(() => {
        treeElement.style.transform = 'scale(1.1)';
        treeElement.style.opacity = '1';
        
        setTimeout(() => {
            treeElement.style.transform = 'scale(1)';
        }, 300);
    }, 300);
}

// Функция для обновления счетчиков без перезагрузки страницы
function updateCounters(data) {
    Object.keys(data).forEach(selector => {
        const element = document.querySelector(selector);
        if (element) {
            // Применяем анимацию к счетчику
            element.classList.add('animate-pulse');
            setTimeout(() => {
                element.textContent = data[selector];
                setTimeout(() => {
                    element.classList.remove('animate-pulse');
                }, 500);
            }, 300);
        }
    });
} 