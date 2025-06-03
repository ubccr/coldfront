class MultiSelectLookupInput {
  constructor(widgetName, cssUri) {
    this.widgetName = widgetName;
    this.outputElement = document.getElementById(`${widgetName}-output`);
    this.outputListElement = document.getElementById(
      `${widgetName}-output-list`
    );

    if (this.outputElement.value === "None") {
      this.outputElement.value = "";
    }

    this.injectCSS(cssUri);
    this.addButtonListener();
    this.addInitialValues();
    this.handleErrors();
  }

  addButtonListener = () => {
    const addButtonElement = document.getElementById(
      `${this.widgetName}-add-button`
    );
    addButtonElement.addEventListener("click", this.handleAddButtonClick);

    const removeButtonElement = document.getElementById(
      `${this.widgetName}-remove-button`
    );
    removeButtonElement.addEventListener("click", this.handleRemoveButtonClick);
  };

  addErrorMessage = (invalidUsernames) => {
    const errorMessage = `The following usernames could not be validated: ${invalidUsernames.join(
      ", "
    )}`;

    const pElement = document.getElementById(
      `${this.widgetName}-error-message`
    );
    pElement.style = "display: block";

    const strongElement = document.querySelector(
      `#${this.widgetName}-error-message > strong`
    );
    strongElement.innerText = errorMessage;
  };

  addInitialValues = () => {
    const initialValues = this.outputElement.value
      ? this.outputElement.value
          .split(",")
          .map((subValue) => subValue.trim())
          .filter((subValue) => subValue.length)
      : [];

    for (const value of initialValues) {
      this.addOption(value, false);
    }
  };

  addOption = (value, updateValue = true) => {
    const existingMatches = document.querySelector(
      `#${this.widgetName}-output-list > li[value="${value}"]`
    );
    if (existingMatches === null) {
      const liValues = this.outputElement.value
        .split(",")
        .filter((outputValue) => outputValue.length && outputValue !== value);

      liValues.push(value);
      liValues.sort();

      const liElements = liValues.map(this.createListItemElement);
      this.outputListElement.replaceChildren(...liElements);

      if (updateValue) {
        this.outputElement.value = this.addValueToOutputList(
          this.outputElement.value,
          value
        );
      }
    }
  };

  addValueToOutputList = (outputListStr, value) => {
    if (outputListStr.trim() === "") {
      return value.trim();
    }

    const outputList = outputListStr.split(",");

    return [...outputList, value.trim()]
      .sort((a, b) => a.localeCompare(b))
      .join(",");
  };

  createListItemElement = (value) => {
    const liElement = document.createElement("li");
    liElement.setAttribute("value", value);
    liElement.setAttribute(
      "class",
      "multi-select-lookup list-group-item d-flex flex-row justify-content-between"
    );

    liElement.addEventListener("click", (event) =>
      this.onListItemClick(event, liElement)
    );

    const pElement = document.createElement("p");
    const content = document.createTextNode(value);
    pElement.appendChild(content);

    liElement.appendChild(pElement);

    return liElement;
  };

  handleAddButtonClick = (event) => {
    const inputElement = document.getElementById(`${this.widgetName}-textarea`);

    const values = inputElement.value
      .split(",")
      .map((value) => value.trim())
      .filter((value) => value.length);

    for (const value of values) {
      this.addOption(value, this.widgetName);
    }

    inputElement.value = "";
  };

  handleErrors = () => {
    const errorContainers = Array.from(
      document.querySelectorAll(`[id^=error_][id$=_id_${this.widgetName}]`)
    );
    const invalidUsernames = errorContainers
      .filter((container) => container.className.includes("invalid-feedback"))
      .map((container) => container.innerText);

    if (invalidUsernames.length > 0) {
      const queryString = invalidUsernames
        .map(
          (invalidUsername) =>
            `ul#${this.widgetName}-output-list > li[value="${invalidUsername}"]`
        )
        .join(",");
      const invalidListItems = document.querySelectorAll(queryString);

      this.removeOptions(invalidListItems);

      this.addErrorMessage(invalidUsernames);
    }
  };

  handleRemoveButtonClick = (event) => {
    const listItemElements = document.querySelectorAll(
      `#${this.widgetName}-output-list > li[selected]`
    );

    this.removeOptions(listItemElements);
  };

  injectCSS = (cssUri) => {
    const css = document.querySelector(`link[href='${cssUri}']`);

    if (!css) {
      const file = document.createElement("link");
      file.setAttribute("rel", "stylesheet");
      file.setAttribute("type", "text/css");
      file.setAttribute("href", cssUri);
      document.head.appendChild(file);
    }
  };

  onListItemClick = (event, listItemElement) => {
    if (listItemElement.getAttribute("selected") !== null) {
      listItemElement.removeAttribute("selected");
    } else {
      listItemElement.setAttribute("selected", "");
    }
  };

  removeOptions = (listItemElements) => {
    for (const listItemElement of listItemElements) {
      const value = listItemElement.getAttribute("value");

      this.outputElement.value = this.removeValueFromOutputList(
        this.outputElement.value,
        value
      );

      listItemElement.remove();
    }
  };

  removeValueFromOutputList = (outputListStr, value) => {
    const outputList = outputListStr.split(",");

    return outputList.filter((element) => element !== value).join(",");
  };
}
