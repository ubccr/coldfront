$("#navbar-main > ul > li.active").removeClass("active");
  $("#navbar-project-menu").addClass("active");
  $("#navbar-allocation").addClass("active");

  $(document).on('click', '#form_reset_button', function () {
    resetForm($('#filter_form'));
  });

  $(".datepicker").flatpickr();

  function resetForm($form) {
    $form.find('input:text, input:password, input:file, select, textarea').val('');
    $form.find('input:radio, input:checkbox').removeAttr('checked').removeAttr('selected');
  };

  $("#expand_button").click(function () {
    $('#collapseOne').collapse();
    icon = $("#plus_minus");
    icon.toggleClass("fa-plus fa-minus");
  });