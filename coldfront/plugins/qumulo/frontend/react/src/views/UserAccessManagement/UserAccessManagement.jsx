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
  const [modalState, setModalState] = useState({
    title: "",
    text: "",
    render: false,
    onClose: () => {},
  });

  const cookies = new Cookies();
  const csrfToken = cookies.get("csrftoken");

  const onSubmit = async () => {
    const allocationIds = allocations.map((allocation) => allocation.id);

    const invalidUsers = await getInvalidUsers([...rwUsers, ...roUsers]);

    if (invalidUsers.length > 0) {
      const errorMessage = `The following users were not found: ${invalidUsers.join(
        ", "
      )}`;

      setModalState({
        title: "Invalid Users",
        text: errorMessage,
        render: true,
        onClose: () =>
          setModalState({
            title: "",
            text: "",
            render: false,
            onClose: () => {},
          }),
      });
      return;
    }

    return axios
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
        setModalState({
          title: "Update Submitted",
          text: "Permissions changes have been submitted and will be applied shortly.",
          render: true,
          onClose: () => window.location.reload(),
        });
      })
      .catch((error) => {
        console.error(error);
      });
  };

  const getInvalidUsers = async (users) => {
    const response = await axios.get("/qumulo/api/active-directory-members", {
      params: { members: users },
    });

    const validUsers = response.data.validNames;
    const invalidUsers = users.filter((user) => !validUsers.includes(user));

    return invalidUsers;
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
        getInvalidUsers={getInvalidUsers}
      />
      <UserSelector
        name="ro-user-selector"
        users={roUsers}
        setUsers={setRoUsers}
        label={"Read-Only Users"}
        getInvalidUsers={getInvalidUsers}
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
      {modalState.render && (
        <GenericModal
          title={modalState.title}
          text={modalState.text}
          onClose={modalState.onClose}
        />
      )}
    </>
  );
}

export default UserAccessManagement;
