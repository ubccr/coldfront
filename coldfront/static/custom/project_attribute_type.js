// project_attribute_type.js

document.addEventListener('DOMContentLoaded', function () {
    var isDefaultField = document.querySelector('#id_is_default');
    var isDefaultValueField = document.querySelector('.field-is_default_value');

    function toggleIsDefaultCommand() {
        if (isDefaultField.checked) {
            isDefaultValueField.style.display = 'block';
        } else {
            isDefaultValueField.style.display = 'none';
        }
    }

    if (isDefaultField && isDefaultValueField) {
        toggleIsDefaultCommand();

        isDefaultField.addEventListener('change', function () {
            toggleIsDefaultCommand();
        });
    }
});
