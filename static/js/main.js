// ===============================
// COMPLETE WORKING VERSION - main.js
// ===============================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded');
    
    // Initialize all features
    initializeShelfInteractions();
    setupTimer();
    setupGoalCheckboxes();
    addGoalTrackingStyles();
    
    // Initialize reading stats chart if present
    if (document.getElementById('readingStatsChart')) {
        initializeReadingStatsChart();
    }
});

// ===============================
// SHELF INTERACTIONS (Long Press & Click)
// ===============================
function initializeShelfInteractions() {
    const shelves = document.querySelectorAll('.dashboard-shelf');
    
    shelves.forEach(shelf => {
        let pressTimer;
        let longPress = false;
        let mouseStartX = 0;
        let mouseStartY = 0;
        const MOVE_THRESHOLD = 10;
        
        // Mouse down - start long press timer
        shelf.addEventListener('mousedown', function(e) {
            if (e.target.closest('.rename-btn') || 
                e.target.closest('.delete-btn') || 
                e.target.closest('.start-reading-btn') ||
                e.target.closest('.shelf-actions')) {
                return;
            }
            
            mouseStartX = e.clientX;
            mouseStartY = e.clientY;
            longPress = false;
            
            pressTimer = setTimeout(() => {
                longPress = true;
                showShelfActions(shelf);
            }, 500);
        });
        
        // Track mouse movement
        shelf.addEventListener('mousemove', function(e) {
            if (pressTimer) {
                const moveX = Math.abs(e.clientX - mouseStartX);
                const moveY = Math.abs(e.clientY - mouseStartY);
                
                if (moveX > MOVE_THRESHOLD || moveY > MOVE_THRESHOLD) {
                    clearTimeout(pressTimer);
                    pressTimer = null;
                }
            }
        });
        
        // Mouse up - handle click
        shelf.addEventListener('mouseup', function(e) {
            clearTimeout(pressTimer);
            pressTimer = null;
            
            // Don't navigate if clicking buttons or if long press is active
            if (e.target.closest('.shelf-actions') || longPress) {
                return;
            }
            
            // Normal click - navigate
            const url = shelf.getAttribute('data-url');
            if (url) {
                window.location.href = url;
            }
        });
        
        // Mouse leave - hide actions after delay
        shelf.addEventListener('mouseleave', function() {
            clearTimeout(pressTimer);
            pressTimer = null;
            
            setTimeout(() => {
                if (!shelf.matches(':hover')) {
                    hideShelfActions(shelf);
                    longPress = false;
                }
            }, 2000); // 2 second delay to click buttons
        });
        
        // Touch events for mobile
        let touchStartX = 0;
        let touchStartY = 0;
        
        shelf.addEventListener('touchstart', function(e) {
            if (e.target.closest('.shelf-actions')) {
                return;
            }
            
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            longPress = false;
            
            pressTimer = setTimeout(() => {
                longPress = true;
                showShelfActions(shelf);
                e.preventDefault();
            }, 500);
        });
        
        shelf.addEventListener('touchmove', function(e) {
            if (pressTimer) {
                const moveX = Math.abs(e.touches[0].clientX - touchStartX);
                const moveY = Math.abs(e.touches[0].clientY - touchStartY);
                
                if (moveX > MOVE_THRESHOLD || moveY > MOVE_THRESHOLD) {
                    clearTimeout(pressTimer);
                    pressTimer = null;
                }
            }
        });
        
        shelf.addEventListener('touchend', function(e) {
            clearTimeout(pressTimer);
            pressTimer = null;
            
            if (!longPress && !e.target.closest('.shelf-actions')) {
                const url = shelf.getAttribute('data-url');
                if (url) {
                    window.location.href = url;
                }
            }
        });
    });
    
    // Handle button clicks
    document.addEventListener('click', function(e) {
        // Rename button
        if (e.target.closest('.rename-btn')) {
            e.preventDefault();
            e.stopPropagation();
            
            const btn = e.target.closest('.rename-btn');
            const shelf = btn.closest('.dashboard-shelf');
            const shelfId = shelf.getAttribute('data-id') || btn.getAttribute('data-shelf-id');
            const shelfName = shelf.querySelector('.shelf-text').textContent.trim();
            
            const newName = prompt('Enter new name:', shelfName);
            if (newName && newName.trim() !== '') {
                renameShelf(shelfId, newName.trim(), shelf);
            }
            return false;
        }
        
        // Delete button
        if (e.target.closest('.delete-btn')) {
            e.preventDefault();
            e.stopPropagation();
            
            const btn = e.target.closest('.delete-btn');
            const shelf = btn.closest('.dashboard-shelf');
            const shelfId = shelf.getAttribute('data-id') || btn.getAttribute('data-shelf-id');
            const bookId = btn.getAttribute('data-book-id');
            const itemName = shelf.querySelector('.shelf-text').textContent.trim();
            
            if (bookId) {
                // It's a book
                if (confirm(`Are you sure you want to delete "${itemName}"?`)) {
                    deleteBook(bookId, shelf);
                }
            } else {
                // It's a shelf
                if (confirm(`Are you sure you want to delete "${itemName}"? This will also delete all books in this shelf.`)) {
                    deleteShelf(shelfId, shelf);
                }
            }
            return false;
        }
        
        // Start reading button
        if (e.target.closest('.start-reading-btn')) {
            e.preventDefault();
            e.stopPropagation();
            
            const btn = e.target.closest('.start-reading-btn');
            const bookId = btn.getAttribute('data-book-id');
            
            startReading(bookId);
            return false;
        }
    });
}

function showShelfActions(shelf) {
    const actions = shelf.querySelector('.shelf-actions');
    if (actions) {
        actions.style.display = 'flex';
        setTimeout(() => {
            actions.style.opacity = '1';
        }, 10);
        shelf.classList.add('active');
    }
}

function hideShelfActions(shelf) {
    const actions = shelf.querySelector('.shelf-actions');
    if (actions) {
        actions.style.opacity = '0';
        setTimeout(() => {
            actions.style.display = 'none';
            shelf.classList.remove('active');
        }, 300);
    }
}

// ===============================
// API FUNCTIONS
// ===============================
function renameShelf(shelfId, newName, shelfElement) {
    fetch('/rename_shelf', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: shelfId, name: newName})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            shelfElement.querySelector('.shelf-text').textContent = newName;
            hideShelfActions(shelfElement);
        } else {
            alert('Error renaming: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error renaming. Please try again.');
    });
}

function deleteShelf(shelfId, shelfElement) {
    fetch('/delete_shelf', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: shelfId})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            shelfElement.remove();
        } else {
            alert('Error deleting: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error deleting. Please try again.');
    });
}

function deleteBook(bookId, bookElement) {
    fetch('/delete_book', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: bookId})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            bookElement.remove();
        } else {
            alert('Error deleting book: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error deleting book. Please try again.');
    });
}

function startReading(bookId) {
    fetch(`/start_reading/${bookId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/active_reading';
        } else {
            alert('Failed to start reading');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error starting reading');
    });
}

// ===============================
// READING TIMER WITH AI VOICE
// ===============================
let timerInterval = null;
let remainingTime = 25 * 60;
let isRunning = false;
let hasSpoken = false;

function setupTimer() {
    const display = document.getElementById("timerDisplay");
    const minutesInput = document.getElementById("minutes");
    const startBtn = document.getElementById("startTimer");
    const pauseBtn = document.getElementById("pauseTimer");
    const resetBtn = document.getElementById("resetTimer");
    
    if (!display || !minutesInput || !startBtn || !pauseBtn || !resetBtn) {
        console.log("Timer elements not found");
        return;
    }
    
    function updateDisplay() {
        const mins = Math.floor(remainingTime / 60);
        const secs = remainingTime % 60;
        display.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    }
    
    function speakMessage(message) {
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
            const speech = new SpeechSynthesisUtterance(message);
            speech.lang = "en-US";
            window.speechSynthesis.speak(speech);
        }
    }
    
    startBtn.addEventListener("click", () => {
        if (isRunning) return;
        isRunning = true;
        hasSpoken = false;
        
        if (remainingTime <= 0) {
            const minutes = parseInt(minutesInput.value, 10) || 25;
            remainingTime = minutes * 60;
        }
        
        timerInterval = setInterval(() => {
            if (remainingTime > 0) {
                remainingTime--;
                updateDisplay();
            } else {
                clearInterval(timerInterval);
                isRunning = false;
                if (!hasSpoken) {
                    hasSpoken = true;
                    speakMessage("Reading time completed. Reset your timer.");
                }
            }
        }, 1000);
    });
    
    pauseBtn.addEventListener("click", () => {
        clearInterval(timerInterval);
        isRunning = false;
    });
    
    resetBtn.addEventListener("click", () => {
        clearInterval(timerInterval);
        isRunning = false;
        hasSpoken = false;
        const minutes = parseInt(minutesInput.value, 10) || 25;
        remainingTime = minutes * 60;
        updateDisplay();
    });
    
    minutesInput.addEventListener("change", () => {
        if (!isRunning) {
            const minutes = parseInt(minutesInput.value, 10) || 25;
            remainingTime = minutes * 60;
            updateDisplay();
        }
    });
    
    updateDisplay();
}

// ===============================
// GOAL CHECKBOX HANDLING
// ===============================
function setupGoalCheckboxes() {
    document.addEventListener("change", function(e) {
        if (e.target.classList.contains("goal-checkbox")) {
            const checkbox = e.target;
            const index = parseInt(checkbox.dataset.index);
            
            if (isNaN(index)) {
                console.error("Invalid index");
                return;
            }
            
            fetch("/toggle-task", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({index: index})
            })
            .then(res => res.json())
            .then(data => {
                if (!data.success) {
                    checkbox.checked = !checkbox.checked;
                }
            })
            .catch(err => {
                console.error("Error:", err);
                checkbox.checked = !checkbox.checked;
            });
        }
    });
}

// ===============================
// GOAL TRACKING STYLES
// ===============================
function addGoalTrackingStyles() {
    if (document.querySelector('#goal-tracking-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'goal-tracking-styles';
    style.textContent = `
        .dashboard-shelf {
            position: relative;
            cursor: pointer;
            transition: all 0.2s;
            user-select: none;
        }
        
        .shelf-actions {
            display: none;
            opacity: 0;
            gap: 8px;
            transition: opacity 0.3s ease;
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            z-index: 10;
        }
        
        .rename-btn, .delete-btn, .start-reading-btn {
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid #ddd;
            cursor: pointer;
            font-size: 18px;
            padding: 8px 12px;
            border-radius: 6px;
            transition: all 0.2s;
        }
        
        .rename-btn:hover, .delete-btn:hover, .start-reading-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        
        .rename-btn {
            color: #ffc107;
            border-color: #ffc107;
        }
        
        .delete-btn {
            color: #dc3545;
            border-color: #dc3545;
        }
        
        .start-reading-btn {
            color: #4CAF50;
            border-color: #4CAF50;
        }
        
        .dashboard-shelf.active {
            transform: scale(0.98);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .completed-goal {
            opacity: 0.6;
        }
        
        .completed-goal .goal-title {
            text-decoration: line-through;
            color: #666;
        }
    `;
    document.head.appendChild(style);
}

// ===============================
// READING STATISTICS CHART
// ===============================
function initializeReadingStatsChart() {
    if (typeof Chart === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        script.onload = () => loadReadingStatistics();
        document.head.appendChild(script);
    } else {
        loadReadingStatistics();
    }
}

function loadReadingStatistics() {
    const chartContainer = document.getElementById('readingStatsChart');
    if (!chartContainer) return;
    
    fetch('/api/reading-statistics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderReadingStatsChart(data.statistics);
            }
        })
        .catch(error => console.error('Error:', error));
}

function renderReadingStatsChart(stats) {
    const ctx = document.getElementById('readingStatsChart');
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Completed', 'Active', 'Unread'],
            datasets: [{
                data: [stats.completed_books, stats.active_books, stats.unread_books],
                backgroundColor: ['#4CAF50', '#2196F3', '#BDBDBD'],
                borderColor: ['#fff', '#fff', '#fff'],
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {display: false}
            }
        }
    });
}




// ===============================
// READING STATISTICS CHART
// ===============================
function initializeReadingStatsChart() {
    if (typeof Chart === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        script.onload = () => loadReadingStatistics();
        document.head.appendChild(script);
    } else {
        loadReadingStatistics();
    }
}

function loadReadingStatistics() {
    const chartContainer = document.getElementById('readingStatsChart');
    if (!chartContainer) return;
    
    fetch('/api/reading-statistics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderReadingStatsChart(data.statistics);
                createStatsLabels(data.statistics);
            }
        })
        .catch(error => console.error('Error:', error));
}

function renderReadingStatsChart(stats) {
    const ctx = document.getElementById('readingStatsChart');
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Completed', 'Active Reading', 'Unread'],
            datasets: [{
                data: [stats.completed_books, stats.active_books, stats.unread_books],
                backgroundColor: ['#4CAF50', '#2196F3', '#BDBDBD'],
                borderColor: ['#fff', '#fff', '#fff'],
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {display: false},
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = stats.total_books;
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} books (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function createStatsLabels(stats) {
    const labelsContainer = document.getElementById('readingStatsLabels');
    if (!labelsContainer) return;
    
    labelsContainer.innerHTML = `
        <div style="margin-top: 30px;">
            <!-- Stats Labels -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                <!-- Completed Books -->
                <div style="display: flex; align-items: center; gap: 12px; padding: 12px; background: #e8f5e9; border-radius: 8px;">
                    <div style="width: 16px; height: 16px; background: #4CAF50; border-radius: 50%; flex-shrink: 0;"></div>
                    <div style="flex: 1;">
                        <div style="font-size: 13px; color: #666; margin-bottom: 2px;">Completed Books</div>
                        <div style="font-size: 20px; font-weight: bold; color: #4CAF50;">${stats.completed_books}</div>
                    </div>
                </div>
                
                <!-- Active Reading -->
                <div style="display: flex; align-items: center; gap: 12px; padding: 12px; background: #e3f2fd; border-radius: 8px;">
                    <div style="width: 16px; height: 16px; background: #2196F3; border-radius: 50%; flex-shrink: 0;"></div>
                    <div style="flex: 1;">
                        <div style="font-size: 13px; color: #666; margin-bottom: 2px;">Active Reading</div>
                        <div style="font-size: 20px; font-weight: bold; color: #2196F3;">${stats.active_books}</div>
                    </div>
                </div>
                
                <!-- Unread Books -->
                <div style="display: flex; align-items: center; gap: 12px; padding: 12px; background: #f5f5f5; border-radius: 8px;">
                    <div style="width: 16px; height: 16px; background: #BDBDBD; border-radius: 50%; flex-shrink: 0;"></div>
                    <div style="flex: 1;">
                        <div style="font-size: 13px; color: #666; margin-bottom: 2px;">Unread Books</div>
                        <div style="font-size: 20px; font-weight: bold; color: #9E9E9E;">${stats.unread_books}</div>
                    </div>
                </div>
            </div>
            
            <!-- Total Books Summary -->
            <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; text-align: center; color: white;">
                <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">Total Books in Library</div>
                <div style="font-size: 36px; font-weight: bold;">${stats.total_books}</div>
                <div style="font-size: 14px; opacity: 0.9; margin-top: 8px;">Completion Rate: ${((stats.completed_books / stats.total_books) * 100).toFixed(1)}%</div>
            </div>
        </div>
    `;
}