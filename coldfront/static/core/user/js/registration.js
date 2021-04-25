$(document).ready(function() {

  // Run function when the user stops typing.
  // Source: https://stackoverflow.com/a/4220182
  const divId = 'div_id_email';
  var emailTypingTimer;
  var doneTypingMs = 1000;

  $(`#${divId}`).on('keyup', function() {
    clearTimeout(emailTypingTimer);
    emailTypingTimer = setTimeout(checkEmailAddressExists, doneTypingMs);
  });

  $(`#${divId}`).on('keydown', function() {
    clearTimeout(emailTypingTimer);
  });

});


function checkEmailAddressExists() {
  let div = document.getElementById('id_email');
  let url = `/user/email-address-exists/${div.value}`;
  axios.get(url)
    .then(response => {
      let data = response.data;
      let exists = data.email_address_exists;
      let alertDiv = document.getElementById('emailExists');
      if (exists) {
        let loginUrl = '/user/login';
        let passwordResetUrl = '/user/password-reset';
        let loginTag = '' +
          '<a href="' + loginUrl + '">' +
            'login' +
          '</a>';
        let passwordResetTag = '' +
          '<a href="' + passwordResetUrl + '">' +
            'set your password' +
          '</a>';
        alertDiv.innerHTML = '' +
          'A user with that email address already exists. If this is you, ' +
          'please ' + loginTag + ' or ' + passwordResetTag + ' to gain ' +
          'access.';
      } else {
        alertDiv.innerHTML = '';
      }
    });
};
