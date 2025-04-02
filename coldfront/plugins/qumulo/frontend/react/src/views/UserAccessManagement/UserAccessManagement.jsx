import { useState } from "react";

import UserSelector from "../../components/UserSelector/UserSelector";
import AllocationSelector from "../../components/AllocationSelector/AllocationSelector";
import GenericModal from "../../components/GenericModal/GenericModal";

import axios from "axios";
import Cookies from "universal-cookie";

import "./UserAccessManagement.css";

function UserAccessManagement() {
  const [rwUsers, setRwUsers] = useState([]);
  const [roUsers, setRoUsers] = useState([]);
  const [allocations, setAllocations] = useState([]);
  const [renderModal, setRenderModal] = useState(false);

  const cookies = new Cookies();
  const csrfToken = cookies.get("csrftoken");

  const onSubmit = () => {
    const allocationIds = allocations.map((allocation) => allocation.id);

    axios
      .post(
        "user-access-management",
        {
          rwUsers,
          roUsers,
          allocationIds: allocationIds,
        },
        {
          headers: {
            "X-CSRFToken": csrfToken,
          },
        }
      )
      .then((response) => {
        setRenderModal(true);
      })
      .catch((error) => {
        console.error(error);
      });
  };

  return (
    <>
      <h2>User Access Management</h2>
      <p>
        Selected users will be added to the selected allocations. Existing users
        will not be removed.
      </p>
      <hr />
      <UserSelector
        name="rw-user-selector"
        users={rwUsers}
        setUsers={setRwUsers}
        label={"Read/Write Users"}
      />
      <UserSelector
        name="ro-user-selector"
        users={roUsers}
        setUsers={setRoUsers}
        label={"Read-Only Users"}
      />
      <AllocationSelector
        setSelectedAllocations={setAllocations}
        selectedAllocations={allocations}
        label={"Allocations"}
      />
      <div className="d-flex justify-content-end">
        <button
          type="submit"
          className="btn btn-primary mr-2"
          id="user_management_form_submit"
          onClick={onSubmit}
        >
          Submit
        </button>
      </div>
      <GenericModal
        title="Update Submitted"
        text="Permissions changes have been submitted and will be applied shortly."
        onClose={() => window.location.reload()}
        show={renderModal}
      />
    </>
  );
}

export default UserAccessManagement;
