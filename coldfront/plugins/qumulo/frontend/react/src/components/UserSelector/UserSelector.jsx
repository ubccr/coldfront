import { useState } from "react";

import "./UserSelector.css";

function UserSelector({
  name,
  users,
  setUsers,
  getInvalidUsers = async () => [],
  label,
  errorMessage,
}) {
  const [inputText, setInputText] = useState("");
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [invalidUsers, setInvalidUsers] = useState([]);

  const handleAddButtonClick = async (event) => {
    const values = inputText
      .split(",")
      .map((value) => value.trim())
      .filter((value) => value.length);

    const newUsers = [...users, ...values];
    setUsers(newUsers);
    setInputText("");

    const invalidUsers = await getInvalidUsers(newUsers);
    setInvalidUsers(invalidUsers);
  };

  const handleRemoveButtonClick = (event) => {
    setUsers(users.filter((user) => !selectedUsers.includes(user)));
    setSelectedUsers([]);
  };

  const onListItemClick = (key) => {
    if (selectedUsers.includes(key)) {
      setSelectedUsers(selectedUsers.filter((user) => user !== key));
    } else {
      setSelectedUsers([...selectedUsers, key]);
    }
  };

  const isSelected = (user) => (selectedUsers.includes(user) ? "selected" : "");
  const isInvalid = (user) => invalidUsers.includes(user);

  return (
    <>
      <p
        id={`${name}-error-message`}
        className="invalid-feedback"
        style={{ display: errorMessage ? "block" : "none" }}
      >
        {errorMessage}
      </p>
      <label htmlFor={`${name}-textarea`} className="form-label">
        {label}:
      </label>
      <div className="d-flex flex-row justify-content-between">
        <textarea
          id={`${name}-textarea`}
          className="align-self-start"
          rows="4"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        ></textarea>
        <div className="btn-group-vertical align-self-start">
          <button
            id={`${name}-add-button`}
            type="button"
            className="btn btn-outline-primary btn-md"
            onClick={handleAddButtonClick}
          >
            &raquo;
          </button>
          <button
            id={`${name}-remove-button`}
            type="button"
            className="btn btn-outline-primary btn-md"
            onClick={handleRemoveButtonClick}
          >
            &laquo;
          </button>
        </div>
        <ul
          id={`${name}-output-list`}
          className="list-group multi-select-lookup"
        >
          {users.map((user) => (
            <li
              className={`multi-select-lookup list-group-item d-flex flex-row justify-content-between ${isSelected(
                user
              )}`}
              onClick={() => onListItemClick(user)}
              key={user}
            >
              {user}
              {isInvalid(user) && (
                <p className="invalid-feedback invalid-user">Invalid User</p>
              )}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

export default UserSelector;
