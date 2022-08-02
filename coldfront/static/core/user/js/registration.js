$(document).ready(function() {

  // Run a function when the user stops typing.
  // Source: https://stackoverflow.com/a/4220182
  var doneTypingMs = 200;


  // Detect when the user stops typing in the email fields.
  const emailDivId = 'div_id_email';
  var emailTypingTimer;

  $(`#${emailDivId}`).on('keyup', function() {
    clearTimeout(emailTypingTimer);
    emailTypingTimer = setTimeout(checkEmailAddressExists, doneTypingMs);
  });

  $(`#${emailDivId}`).on('keydown', function() {
    clearTimeout(emailTypingTimer);
  });


  // Detect when the user stops typing in the first and last name fields.
  const firstNameDivId = 'div_id_first_name';
  const lastNameDivId = 'div_id_last_name';
  var nameTypingTimer;
  let namesSelector = `#${firstNameDivId}, #${lastNameDivId}`;

  $(namesSelector).on('keyup', function() {
    clearTimeout(nameTypingTimer);
    nameTypingTimer = setTimeout(checkNameExists, doneTypingMs);
  });

  $(namesSelector).on('keydown', function() {
    clearTimeout(emailTypingTimer);
  });


  // When the acknowledgement check box changes, conditionally display the
  // registration button.
  let ackDivId = 'new-user-acknowledgement';
  $(`#${ackDivId}`).change(function() {
    let registerButton = document.getElementById('register-button');
    var display;
    if (this.checked) {
      display = 'block';
    } else {
      display = 'none';
    }
    registerButton.style.display = display;
  });

});


const loginTag = '' +
  '<a href="/user/login">' +
    'login' +
  '</a>';
const passwordResetTag = '' +
  '<a href="/user/password-reset">' +
    'set your password' +
  '</a>';


function checkEmailAddressExists() {
  let email = document.getElementById('id_email').value;
  let url = `/user/email-address-exists/${email}`;
  axios.get(url)
    .then(response => {
      let data = response.data;
      let exists = data.email_address_exists;
      let alertDiv = document.getElementById('emailExists');
      if (exists) {
        alertDiv.innerHTML = '' +
          'A user with that email address already exists. If this is you, ' +
          'please ' + loginTag + ' or ' + passwordResetTag + ' to gain ' +
          'access. You may then associate additional email addresses with ' +
          'your account. If you need any assistance, please contact us.';
      } else {
        alertDiv.innerHTML = '';
      }
    });
};


function checkNameExists() {
  let firstName = document.getElementById('id_first_name').value;
  let lastName = document.getElementById('id_last_name').value;

  let pattern = /^[A-Za-z\-]+$/;
  let isFirstNameValid = firstName.length > 0 && pattern.test(firstName);
  let isLastNameValid = lastName.length > 0 && pattern.test(lastName);

  let alertDiv = document.getElementById('nameExists');
  let ackDiv = document.getElementById('new-user-acknowledgement-form');
  let ackInput = document.getElementById('new-user-acknowledgement');
  let registerButton = document.getElementById('register-button');

  if (isFirstNameValid && isLastNameValid) {
    let url = `` +
      `/user/user-name-exists?first_name=${firstName}&last_name=${lastName}`;
    axios.get(url)
      .then(response => {
        let data = response.data;
        let exists = data.name_exists;
        if (exists) {
          let program_name_short = JSON.parse(
            document.getElementById('program_name_short').textContent);
          alertDiv.innerHTML = '' +
            'A user with the provided first and last name already exists. ' +
            'If you have previously used a ' + program_name_short +
            ' cluster, you should already have an account. If so, please ' +
            loginTag + ' or ' + passwordResetTag + ' using the existing ' +
            'address to gain access. You may then associate additional ' +
            'email addresses with your account. If you need any assistance, ' +
            'please contact us.';
          ackDiv.style.display = 'block';
          registerButton.style.display = 'none';
        } else {
          alertDiv.innerHTML = '';
          ackDiv.style.display = 'none';
          registerButton.style.display = 'block';
        }
      });
  } else {
    alertDiv.innerHTML = '';
    ackDiv.style.display = 'none';
    registerButton.style.display = 'block';
  }
  ackInput.checked = false;
};
