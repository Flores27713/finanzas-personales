import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Empty State for funny alert
old_alert = '''        function updateFunnyAlert(totalSpent, totalBudget) {
            const pct = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;
            const alertData = FUNNY_QUOTES.find(q => pct <= q.maxPct) || FUNNY_QUOTES[FUNNY_QUOTES.length - 1];'''

new_alert = '''        function updateFunnyAlert(totalSpent, totalBudget) {
            if (totalSpent === 0) {
                const box = document.getElementById('funny-alert-box');
                const iconEl = document.getElementById('funny-alert-icon');
                const titleEl = document.getElementById('funny-alert-title');
                const msgEl = document.getElementById('funny-alert-msg');
                box.className = 'glass-card rounded-2xl p-4 border-l-4 border-emerald-500 flex items-center gap-3 transition-all duration-300 shadow-lg';
                iconEl.className = 'w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center text-xl shrink-0';
                iconEl.innerHTML = '<i class="fa-solid fa-piggy-bank"></i>';
                titleEl.innerText = "¡TODO EN ORDEN!";
                msgEl.innerText = '"Aún no has gastado nada este mes, tu billetera está a salvo... por ahora."';
                return;
            }
            
            const pct = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;
            const alertData = FUNNY_QUOTES.find(q => pct <= q.maxPct) || FUNNY_QUOTES[FUNNY_QUOTES.length - 1];'''

content = content.replace(old_alert, new_alert)

# 2. Add Export CSV button to Historial
old_historial = '''        <!-- Historial de Transacciones -->
        <section class="space-y-3">
            <h2 class="text-sm font-bold uppercase tracking-wider text-slate-600">Últimas Transacciones</h2>
            <div class="glass-card rounded-2xl p-4 overflow-hidden">'''

new_historial = '''        <!-- Historial de Transacciones -->
        <section class="space-y-3">
            <div class="flex items-center justify-between">
                <h2 class="text-sm font-bold uppercase tracking-wider text-slate-600">Últimas Transacciones</h2>
                <a href="/api/transactions/export" class="text-xs text-emerald-600 hover:text-emerald-700 font-bold flex items-center gap-1.5 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200 hover:bg-emerald-100 transition-all">
                    <i class="fa-solid fa-file-excel"></i> Exportar a Excel
                </a>
            </div>
            <div class="glass-card rounded-2xl p-4 overflow-hidden">'''

content = content.replace(old_historial, new_historial)

# 3. Hide Admin Panel based on role
old_ui_update = '''        function updateUserHeaderUI(user) {
            document.getElementById('header-user-name').innerText = user.name;
            const avatar = document.getElementById('user-avatar');
            if (user.picture) {
                avatar.innerHTML = `<img src="${user.picture}" class="w-full h-full object-cover">`;
            } else {
                avatar.innerHTML = `<i class="fa-solid fa-user text-white text-lg"></i>`;
            }
        }'''

new_ui_update = '''        function updateUserHeaderUI(user) {
            document.getElementById('header-user-name').innerText = user.name;
            const avatar = document.getElementById('user-avatar');
            if (user.picture) {
                avatar.innerHTML = `<img src="${user.picture}" class="w-full h-full object-cover">`;
            } else {
                avatar.innerHTML = `<i class="fa-solid fa-user text-white text-lg"></i>`;
            }
            
            const adminBtn = document.getElementById('admin-panel-btn');
            if (adminBtn) {
                if (user.is_admin) {
                    adminBtn.classList.remove('hidden');
                } else {
                    adminBtn.classList.add('hidden');
                }
            }
        }'''

content = content.replace(old_ui_update, new_ui_update)


with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
