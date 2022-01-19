/**
 * If any form was modified, raise a warning before the user may leave.
 */
$(document).ready(function() {
    $('form').each(function() {
        $(this).dirty({preventLeaving: true});
    });
});
