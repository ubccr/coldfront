$(document).ready(function() {

  // Hide "This field is required." errors. This is a temporary fix
  // needed due to the fact that the form does not seem to appear on
  // the initial page load in some cases.

  for (let i = 1; i <= 2; i++) {
    let passwordField = document.getElementById(`id_new_password${i}`);
    let next = passwordField.nextElementSibling;
    if (next.id === `error_1_id_new_password${i}`) {
      if (next.innerText === 'This field is required.') {
        passwordField.classList.remove('is-invalid');
      }
    }
  }

});
