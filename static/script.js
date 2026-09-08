let sessionId = null;
let currentRating = null;
let isProcessing = false;  // Флаг для предотвращения повторных вызовов

async function startSurvey() {
    showLoading();
    try {
        const resp = await fetch('/api/start');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        sessionId = data.session_id;
        showQuestion(data.question, data);
    } catch (e) {
        console.error(e);
        showError(e.message);
    }
}

function showQuestion(q, progress) {
    let html = '<div class="question">' + q.text + '</div>';
    if (q.context) html = '<div class="context">' + q.context + '</div>' + html;

    if (progress && progress.is_salary) {
        html += '<input type="number" class="salary-input" id="salaryInput" placeholder="100000" value="100000"><button class="next-btn" id="nextBtn">Получить рекомендации</button>';
        document.getElementById('surveyContainer').innerHTML = html;
        document.getElementById('nextBtn').onclick = () => {
            if (isProcessing) return;  // Защита от повторных кликов
            let val = parseInt(document.getElementById('salaryInput').value) || 100000;
            submitAnswer('salary', val);
        };
    } else {
        html += '<div class="rating-buttons">' + [1,2,3,4,5].map(v => '<div class="rating-btn" data-value="'+v+'"><div class="rating-value">'+v+'</div><div class="rating-label">'+['Очень низкий','Низкий','Средний','Высокий','Очень высокий'][v-1]+'</div></div>').join('') + '</div><button class="next-btn" id="nextBtn" disabled>Далее</button>';
        document.getElementById('surveyContainer').innerHTML = html;
        currentRating = null;
        document.querySelectorAll('.rating-btn').forEach(btn => {
            btn.onclick = () => {
                document.querySelectorAll('.rating-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                currentRating = parseInt(btn.dataset.value);
                document.getElementById('nextBtn').disabled = false;
            };
        });
        document.getElementById('nextBtn').onclick = () => {
            if (currentRating && !isProcessing) {
                submitAnswer(q.id, currentRating);
            }
        };
    }
}

async function submitAnswer(qId, ans) {
    if (isProcessing) return;  // Защита от повторных вызовов
    isProcessing = true;

    showLoading();
    try {
        const resp = await fetch('/api/answer', {
            method: 'POST',  // Явно указываем POST
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, question_id: qId, answer: ans })
        });
        const data = await resp.json();
        if (data.done) {
            showResults(data.recommendations, data.stats);
        } else if (data.question) {
            showQuestion(data.question, data);
        } else {
            showError('Ошибка сервера');
        }
    } catch (e) {
        console.error(e);
        showError(e.message);
    } finally {
        isProcessing = false;
    }
}

function showResults(recommendations, stats) {
    const colors = { IDEAL: '#10b981', EXCELLENT: '#3b82f6', GOOD: '#f59e0b', AVERAGE: '#8b5cf6', LOW: '#ef4444' };

    // Отладка - проверяем, что пришло
    console.log('=== ПОЛУЧЕННЫЕ ДАННЫЕ ===');
    console.log('Рекомендации:', recommendations);
    if (recommendations && recommendations[0]) {
        console.log('Первая рекомендация:', recommendations[0]);
        console.log('Explanation:', recommendations[0].explanation);
    }

    let html = '<div class="result-card"><h2>🎓 Рекомендации</h2>';
    html += '<div class="info-note">📊 Каждое направление оценивается независимо (0-100%)</div>';

    for (let rec of recommendations) {
        html += '<div class="recommendation-card">';
        html += '<div class="recommendation-header">';
        html += '<div class="recommendation-rank">' + rec.rank + '</div>';
        html += '<div class="recommendation-title"><strong>' + rec.field + '</strong></div>';
        html += '<div class="recommendation-prob">' + rec.probability + '%</div>';
        html += '<div class="match-badge" style="background:' + colors[rec.match_level] + '">' + rec.match_level + '</div>';
        html += '</div>';

        if (rec.description) {
            html += '<div class="direction-desc">📖 ' + rec.description + '</div>';
        }

        // Показываем объяснение
        if (rec.explanation && rec.explanation.trim().length > 0) {
            html += '<div class="explanation">';
            html += '<div class="explanation-title">💡 Почему это направление?</div>';
            html += '<div class="explanation-text">' + rec.explanation + '</div>';
            html += '</div>';
        } else {
            html += '<div class="explanation">';
            html += '<div class="explanation-title">💡 Почему это направление?</div>';
            html += '<div class="explanation-text">На основе ваших ответов, это направление подходит вам на ' + rec.probability + '%</div>';
            html += '</div>';
        }

        if (rec.key_skills) {
            html += '<div class="skills">🔧 Ключевые навыки: ' + rec.key_skills + '</div>';
        }

        html += '</div>';
    }

    html += '<button class="restart-btn" onclick="location.reload()">🔄 Пройти заново</button>';
    html += '</div>';

    if (stats) {
        html += '<div class="stats">';
        html += '<div class="stat-item"><div class="stat-value">' + (stats.questions_asked || 0) + '</div><div class="stat-label">Задано вопросов</div></div>';
        html += '</div>';
    }

    document.getElementById('surveyContainer').innerHTML = html;
}

function showLoading() {
    document.getElementById('surveyContainer').innerHTML = '<div class="loading"><div class="spinner"></div><p>Загрузка...</p></div>';
}

function showError(err) {
    document.getElementById('surveyContainer').innerHTML = '<div class="result-card"><h2>❌ Ошибка</h2><p style="color:#f44336;text-align:center">' + err + '</p><button class="restart-btn" onclick="location.reload()">🔄 Попробовать снова</button></div>';
}

document.addEventListener('DOMContentLoaded', startSurvey);