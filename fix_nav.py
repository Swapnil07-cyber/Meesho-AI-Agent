with open('intake_app.py', 'r', encoding='utf-8') as f:    content = f.read()

old = '''    nav = [
        ("/", "Dashboard"),
        ("/intake", "Intake"),
        ("/products", "Products"),
        ("/edit_products", "Edit Products"),
        ("/compare", "Compare"),
        ("/profit", "Profit"),
        ("/adstudio", "Ad Studio"),
        ("/scheduler", "Scheduler"),
        ("/marketing", "Marketing"),
        ("/customers", "Customers"),
        ("/orders", "Orders"),
        ("/reports", "Reports"),
        ("/guide", "Guide"),
    ]'''

new = '''    nav = [
        ("/", "Dashboard", ""),
        ("/intake", "Intake", ""),
        ("/products", "Products", ""),
        ("/edit_products", "Edit Products", ""),
        ("/compare", "Compare", ""),
        ("/profit", "Profit", ""),
        ("/adstudio", "Ad Studio", ""),
        ("/scheduler", "Scheduler", ""),
        ("/marketing", "Marketing", ""),
        ("/customers", "Customers", ""),
        ("/orders", "Orders", ""),
        ("/reports", "Reports", ""),
        ("/guide", "Guide", ""),
    ]'''

if old in content:
    content = content.replace(old, new)
    with open('intake_app.py', 'w', encoding='utf-8') as f:        f.write(content)
    print('FIXED: NAV updated to 3 values')
else:
    print('Pattern not found')
    idx = content.find('nav = [')
    if idx >= 0:
        print(content[idx:idx+400])