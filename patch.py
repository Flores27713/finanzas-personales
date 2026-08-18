import re
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_populate = '''                    expCatSelect.innerHTML = cachedCategories.map(cat => `<option value="${cat.id}">🏷️ ${cat.name}</option>`).join('');
                }'''

new_populate = '''                    expCatSelect.innerHTML = cachedCategories.map(cat => `<option value="${cat.id}">🏷️ ${cat.name}</option>`).join('');
                }
                expCatSelect.innerHTML += `<option value="new_cat" class="font-bold text-indigo-600">+ Crear nueva destinación...</option>`;'''

html = html.replace(old_populate, new_populate)

script_end = '''        // Event Listeners Initialization'''
new_listener = '''        document.getElementById('exp-category')?.addEventListener('change', async function(e) {
            if (e.target.value === 'new_cat') {
                const newCatName = prompt("Ingresa el nombre de la nueva destinación (ej. Uber, Comida, etc.):");
                if (newCatName && newCatName.trim() !== '') {
                    try {
                        const response = await fetch('/api/categories', {
                            method: 'POST',
                            headers: getAuthHeaders(),
                            body: JSON.stringify({ name: newCatName.trim(), monthly_budget: 0 })
                        });
                        if (response.ok) {
                            await fetchDashboardData();
                            // Select the newly created category
                            const createdCat = cachedCategories.find(c => c.name.toLowerCase() === newCatName.trim().toLowerCase());
                            if (createdCat) {
                                e.target.value = createdCat.id;
                            }
                            showToast('Destinación creada exitosamente');
                        } else {
                            showToast('Error al crear destinación', 'error');
                            e.target.value = cachedCategories[0]?.id || "";
                        }
                    } catch (error) {
                        console.error(error);
                        showToast('Error de conexión', 'error');
                        e.target.value = cachedCategories[0]?.id || "";
                    }
                } else {
                    e.target.value = cachedCategories[0]?.id || "";
                }
            }
        });

        // Event Listeners Initialization'''

html = html.replace(script_end, new_listener)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
