
def validator(attribute_type, attribute_value):
    if attribute_type != type(attribute_value):
        if attribute_type == 'Yes/No' and attribute_value not in ['Yes','No']:
            if attribute_type == 'Attribute Expanded Text' and type(attribute_value) != str:
                return f'Incorrect value for type {attribute_type}, you entered {attribute_value}'
    return None 