const protocols = Array.from(
  document.querySelectorAll(
    "#div_id_protocols div div.form-check input.form-check-input"
  )
);

const nfsCheckBox = protocols.find((protocol) => protocol.value === "nfs");
const allocationName = document.getElementById("id_storage_name");

nfsCheckBox.addEventListener("change", handleExportPathInput);
allocationName.addEventListener("change", (evt) => {
  document.getElementById("id_storage_filesystem_path").value =
    evt.target.value;
});

if (!nfsCheckBox.checked) {
  document.getElementById("div_id_storage_export_path").style.visibility =
    "hidden";
}

let confirmed = false;

const submitButton = document.getElementById("allocation_form_submit");
submitButton.addEventListener("click", (event) => {
  const id_project_pk_elem = document.getElementById("div_id_project_pk");
  const smb = protocols.find((protocol) => protocol.value === "smb");

  // NOTE: we're using id_project_pk to determine whether we are on a
  // parent or sub-allocation creation page
  if (id_project_pk_elem && !smb.checked && !confirmed) {
    const modal = $("#smb_warning_modal");
    modal.modal("show");

    event.preventDefault();
  }
});


const dialogSubmitButton = document.getElementById("smb_warning_button_submit");
dialogSubmitButton.addEventListener("click", (event) => {
  confirmed = true;

  const modal = $("#smb_warning_modal");
  modal.modal("hide");

  submitButton.click();
  confirmed = false;
});

function handleExportPathInput(event) {
  const isChecked = event.target.checked;

  if (isChecked) {
    document.getElementById("id_storage_export_path").value = "";
    document.getElementById("div_id_storage_export_path").style.visibility =
      "visible";
  } else {
    document.getElementById("div_id_storage_export_path").style.visibility =
      "hidden";
    document.getElementById("id_storage_export_path").value = "";
  }
}
