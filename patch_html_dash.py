import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update the dashboard banner to include Deuda TC and Sueldo
old_banner = '''                    <span class="px-3 py-1.5 rounded-xl bg-white/15 text-emerald-200 font-semibold flex items-center gap-1.5">
                        <i class="fa-solid fa-shield-check text-emerald-200"></i> Libre Real: <strong id="free-balance">$0</strong>
                    </span>'''

new_banner = '''                    <span class="px-3 py-1.5 rounded-xl bg-white/15 text-emerald-200 font-semibold flex items-center gap-1.5">
                        <i class="fa-solid fa-shield-check text-emerald-200"></i> Libre Real: <strong id="free-balance">$0</strong>
                    </span>
                    <span class="px-3 py-1.5 rounded-xl bg-white/15 text-rose-200 font-semibold flex items-center gap-1.5">
                        <i class="fa-solid fa-credit-card text-rose-200"></i> Deuda TC: <strong id="credit-debt">$0</strong>
                    </span>
                    <span class="px-3 py-1.5 rounded-xl bg-white/10 text-indigo-100 font-semibold flex items-center gap-1.5" title="Sueldo/Ingreso Mensual Base">
                        <i class="fa-solid fa-sack-dollar text-indigo-100"></i> Sueldo: <strong id="monthly-income-disp">$0</strong>
                    </span>'''

html = html.replace(old_banner, new_banner)

# 2. Update JS fetchDashboard to update the new DOM elements
old_js = '''                document.getElementById('total-balance').innerText = formatCLP(data.total_balance);
                document.getElementById('daily-hormiga-limit').innerText = `${formatCLP(data.daily_hormiga_limit)} / día`;
                document.getElementById('days-remaining').innerText = `${data.days_remaining_in_month} días restantes`;
                document.getElementById('committed-expenses').innerText = formatCLP(data.committed_expenses || 0);
                document.getElementById('free-balance').innerText = formatCLP(data.free_balance || 0);'''

new_js = '''                document.getElementById('total-balance').innerText = formatCLP(data.total_balance);
                document.getElementById('daily-hormiga-limit').innerText = `${formatCLP(data.daily_hormiga_limit)} / día`;
                document.getElementById('days-remaining').innerText = `${data.days_remaining_in_month} días restantes`;
                document.getElementById('committed-expenses').innerText = formatCLP(data.committed_expenses || 0);
                document.getElementById('free-balance').innerText = formatCLP(data.free_balance || 0);
                
                const creditDebtEl = document.getElementById('credit-debt');
                if (creditDebtEl) creditDebtEl.innerText = formatCLP(data.credit_debt || 0);
                
                const incomeEl = document.getElementById('monthly-income-disp');
                if (incomeEl) incomeEl.innerText = formatCLP(data.monthly_income || 0);'''

html = html.replace(old_js, new_js)

# 3. Update category creation prompt to ask if is_fixed
old_prompt = '''                const newCatName = prompt("Ingresa el nombre de la nueva destinación (ej. Uber, Comida, etc.):");
                if (newCatName && newCatName.trim() !== '') {
                    try {
                        const response = await fetch('/api/categories', {
                            method: 'POST',
                            headers: getAuthHeaders(),
                            body: JSON.stringify({ name: newCatName.trim(), monthly_budget: 0 })
                        });'''

new_prompt = '''                const newCatName = prompt("Ingresa el nombre de la nueva destinación (ej. Uber, Comida, etc.):");
                if (newCatName && newCatName.trim() !== '') {
                    const isFixed = confirm("¿Es este un gasto fijo mensual (ej. arriendo, Netflix, internet)?\\n\\n[Aceptar = Sí] - [Cancelar = No]");
                    try {
                        const response = await fetch('/api/categories', {
                            method: 'POST',
                            headers: getAuthHeaders(),
                            body: JSON.stringify({ name: newCatName.trim(), monthly_budget: 0, is_fixed: isFixed })
                        });'''

html = html.replace(old_prompt, new_prompt)


with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
