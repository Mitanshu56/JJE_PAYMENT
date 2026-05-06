# Read the file
with open('backend/app/routes/chatbot_routes.py', 'r') as f:
    lines = f.readlines()

# Find and remove the misplaced elif block and fix
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if this is the misplaced elif (8 spaces + elif month_hint)
    if line.startswith('        elif month_hint and any(word in text for word in'):
        # Skip this elif block and the next 7 lines
        i += 8
        # Now, before the next elif count_query, insert the correct version
        # Find the next elif count_query
        while i < len(lines) and not lines[i].startswith('    elif count_query'):
            new_lines.append(lines[i])
            i += 1
        
        # Insert the correct indentation version
        if i < len(lines):
            new_lines.append('    elif month_hint and any(word in text for word in [\'bill\', \'invoice\', \'invoices\', \'bills\']):\n')
            new_lines.append('        # "bills in december" or "invoices in january" style queries\n')
            new_lines.append('        intent = \'month_bill_count\'\n')
            new_lines.append('        requires_database = True\n')
            new_lines.append('        requires_exact_numeric_answer = True\n')
            new_lines.append('        requires_party_name = False\n')
            new_lines.append('        confidence = 0.9\n')
    else:
        new_lines.append(line)
        i += 1

# Write the file back
with open('backend/app/routes/chatbot_routes.py', 'w') as f:
    f.writelines(new_lines)

print("File fixed successfully!")
