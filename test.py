from datetime import datetime

def generate_class_id(course_code, section):
    # Get last 2 digits of current year
    year = str(datetime.now().year)[2:]        # 2026 → '26'

    # Remove space from course code
    code_clean = course_code.replace(" ", "")  # 'CPT 113' → 'CPT113'

    # Remove dash from section
    section_clean = section.replace("-", "")   # 'CPET-3201' → 'CPET3201'

    # Combine all parts
    class_id = f"{year}-{code_clean}{section_clean}"
    # Result: '26-CPT113CPET3201' ✅

    return class_id


course_code = "CPT 113"
section     = "CPET-3201"

result = generate_class_id(course_code, section)
print(result)  # 26-CPT113CPET3201 ✅