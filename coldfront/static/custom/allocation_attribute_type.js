// allocation_attribute_type.js

document.addEventListener('DOMContentLoaded', function () {
    var hasUsageField = document.querySelector('#id_has_usage');
    var getUsageCommandField = document.querySelector('.field-get_usage_command');

    function toggleGetUsageCommand() {
        if (hasUsageField.checked) {
            getUsageCommandField.style.display = 'block';
        } else {
            getUsageCommandField.style.display = 'none';
        }
    }

    if (hasUsageField && getUsageCommandField) {
        toggleGetUsageCommand();

        hasUsageField.addEventListener('change', function () {
            toggleGetUsageCommand();
        });
    }
});
