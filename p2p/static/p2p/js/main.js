document.addEventListener('DOMContentLoaded', function() {
  // Создаем декоративные монеты на фоне
  createCoins();
  
  // Инициализируем выпадающие списки
  initDropdowns();
  
  // Инициализируем табы
  initTabs();
  
  // Инициализируем обработчики для модальных окон
  initModals();
  
  // Инициализируем обработчики сообщений
  initChat();
  
  // Добавляем анимацию для карточек
  animateCards();
  
  // Обработчики для форм
  setupForms();
});

// Создание случайных монеток на фоне
function createCoins() {
  const bgDecoration = document.querySelector('.bg-decoration');
  if (!bgDecoration) return;
  
  const coins = ['coin.svg', 'ton-coin.svg', 'not-coin.svg'];
  const coinCount = 15;
  
  for (let i = 0; i < coinCount; i++) {
    const coin = document.createElement('div');
    coin.classList.add('coin');
    
    // Случайное положение
    const left = Math.random() * 100;
    const top = Math.random() * 80;
    
    // Случайный размер
    const size = 20 + Math.random() * 20;
    
    // Случайная монета
    const coinImage = coins[Math.floor(Math.random() * coins.length)];
    
    // Случайная задержка анимации
    const delay = Math.random() * 10;
    
    // Применяем стили
    coin.style.left = `${left}%`;
    coin.style.top = `${top}%`;
    coin.style.width = `${size}px`;
    coin.style.height = `${size}px`;
    coin.style.backgroundImage = `url('../img/${coinImage}')`;
    coin.style.animationDelay = `${delay}s`;
    
    bgDecoration.appendChild(coin);
  }
}

// Инициализация выпадающих списков
function initDropdowns() {
  const dropdowns = document.querySelectorAll('.dropdown-toggle');
  
  dropdowns.forEach(dropdown => {
    dropdown.addEventListener('click', function(e) {
      e.preventDefault();
      const dropdownMenu = this.nextElementSibling;
      
      // Закрываем другие выпадающие списки
      document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
        if (menu !== dropdownMenu) {
          menu.classList.remove('show');
        }
      });
      
      // Переключаем текущий
      dropdownMenu.classList.toggle('show');
    });
  });
  
  // Закрытие выпадающих списков при клике вне их
  document.addEventListener('click', function(e) {
    if (!e.target.matches('.dropdown-toggle') && !e.target.closest('.dropdown-menu')) {
      document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
        menu.classList.remove('show');
      });
    }
  });
}

// Инициализация табов
function initTabs() {
  const tabLinks = document.querySelectorAll('.tab-link');
  
  tabLinks.forEach(tab => {
    tab.addEventListener('click', function(e) {
      e.preventDefault();
      
      const targetId = this.getAttribute('data-target');
      const targetTab = document.querySelector(targetId);
      
      if (!targetTab) return;
      
      // Деактивируем все табы
      document.querySelectorAll('.tab-link').forEach(link => {
        link.classList.remove('active');
      });
      
      document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
      });
      
      // Активируем выбранный таб
      this.classList.add('active');
      targetTab.classList.add('active');
    });
  });
}

// Инициализация модальных окон
function initModals() {
  const modalTriggers = document.querySelectorAll('[data-toggle="modal"]');
  
  modalTriggers.forEach(trigger => {
    trigger.addEventListener('click', function(e) {
      e.preventDefault();
      
      const targetId = this.getAttribute('data-target');
      const targetModal = document.querySelector(targetId);
      
      if (!targetModal) return;
      
      // Открываем модальное окно
      targetModal.classList.add('show');
      document.body.classList.add('modal-open');
      
      // Закрытие по клику на крестик
      const closeButtons = targetModal.querySelectorAll('.modal-close');
      closeButtons.forEach(button => {
        button.addEventListener('click', function() {
          targetModal.classList.remove('show');
          document.body.classList.remove('modal-open');
        });
      });
      
      // Закрытие по клику на фон
      targetModal.addEventListener('click', function(e) {
        if (e.target === this) {
          targetModal.classList.remove('show');
          document.body.classList.remove('modal-open');
        }
      });
    });
  });
}

// Инициализация чата
function initChat() {
  const chatContainer = document.querySelector('.chat-container');
  if (!chatContainer) return;
  
  // Прокрутка чата вниз при загрузке
  chatContainer.scrollTop = chatContainer.scrollHeight;
  
  // Отправка сообщения
  const messageForm = document.querySelector('.message-form');
  if (messageForm) {
    messageForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const messageInput = this.querySelector('.message-input');
      const message = messageInput.value.trim();
      
      if (message) {
        // В реальном приложении здесь был бы AJAX-запрос
        // Для демонстрации добавляем сообщение в DOM
        addMessageToChat(message, true);
        messageInput.value = '';
        
        // Прокручиваем чат вниз
        chatContainer.scrollTop = chatContainer.scrollHeight;
      }
    });
  }
}

// Добавление сообщения в чат (для демонстрации)
function addMessageToChat(message, isOutgoing) {
  const chatContainer = document.querySelector('.chat-container');
  if (!chatContainer) return;
  
  const messageEl = document.createElement('div');
  messageEl.classList.add('message');
  messageEl.classList.add(isOutgoing ? 'message-outgoing' : 'message-incoming');
  
  const now = new Date();
  const timeString = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
  
  messageEl.innerHTML = `
    <div class="message-content">
      ${message}
      <div class="message-time">${timeString}</div>
    </div>
  `;
  
  chatContainer.appendChild(messageEl);
}

// Анимация появления карточек
function animateCards() {
  const cards = document.querySelectorAll('.card');
  
  cards.forEach((card, index) => {
    card.classList.add('fade-in');
    card.style.animationDelay = `${index * 0.1}s`;
  });
}

// Настройка форм
function setupForms() {
  const forms = document.querySelectorAll('form');
  
  forms.forEach(form => {
    form.addEventListener('submit', function(e) {
      // Валидация форм (для простоты просто проверяем заполнение обязательных полей)
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;
      
      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          isValid = false;
          field.classList.add('is-invalid');
        } else {
          field.classList.remove('is-invalid');
        }
      });
      
      if (!isValid) {
        e.preventDefault();
      }
    });
    
    // Удаляем ошибки при вводе
    const formFields = form.querySelectorAll('.form-control');
    formFields.forEach(field => {
      field.addEventListener('input', function() {
        if (this.value.trim()) {
          this.classList.remove('is-invalid');
        }
      });
    });
  });
} 