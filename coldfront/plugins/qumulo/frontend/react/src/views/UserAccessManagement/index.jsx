import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import UserAccessManagement from "./UserAccessManagement.jsx";

createRoot(document.getElementById("user-access-management")).render(
  <StrictMode>
    <UserAccessManagement />
  </StrictMode>
);
