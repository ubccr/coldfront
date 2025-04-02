import { useActionState, useEffect, useState } from "react";
import axios from "axios";

import InputLabel from "../InputLabel/InputLabel";
import PageSelector from "../PageSelector/PageSelector";
import SortButtons from "../SortButtons/SortButtons";
import Table from "../Table/Table";
import Row from "../Row/Row";

import "./AllocationSelector.css";

function AllocationSelector({
  setSelectedAllocations,
  selectedAllocations,
  label,
}) {
  const columns = [
    { key: "id", label: "ID" },
    { key: "resources__name", label: "Resource" },
    { key: "status__name", label: "Status" },
    { key: "attributes__storage_filesystem_path", label: "File Path" },
  ];

  const onQueryChange = (state, { action, key, value }) => {
    switch (action) {
      case "filter":
        return {
          ...state,
          filters: { ...state.filters, [key]: value },
        };
      case "sort":
        return {
          ...state,
          sort: value,
        };
      case "page":
        return {
          ...state,
          page: value,
        };
      default:
        return state;
    }
  };

  const [allocations, setAllocations] = useState([]);
  const [totalPages, setTotalPages] = useState(0);
  const [allChecked, setAllChecked] = useState(false);
  const [queryState, queryDispatch] = useActionState(onQueryChange, {
    filters: {},
    page: 1,
    sort: "id",
  });

  useEffect(() => {
    const params = { search: [], sort: queryState.sort, page: queryState.page };

    for (const [key, value] of Object.entries(queryState.filters)) {
      params.search.push(`${key}:${value}`);
    }

    setAllChecked(false);
    getAllocations(params).then(({ allocations, totalPages }) => {
      setAllocations(allocations);
      setTotalPages(totalPages);
    });
  }, [queryState]);

  const onAllocationCheck = (event) => {
    const allocationId = event.target.value;

    if (event.target.checked) {
      const allocation = allocations.find(
        (allocation) => allocation.id === Number(allocationId)
      );
      setSelectedAllocations([...selectedAllocations, allocation]);
    } else {
      setSelectedAllocations(
        selectedAllocations.filter(
          (allocation) => allocation.id !== Number(allocationId)
        )
      );
      setAllChecked(false);
    }
  };

  const onCheckAll = (event) => {
    if (event.target.checked) {
      const uniqueAllocationIds = new Set([
        ...selectedAllocations.map((allocation) => allocation.id),
        ...allocations.map((allocation) => allocation.id),
      ]);

      const uniqueAllocations = Array.from(uniqueAllocationIds).map((id) => {
        let allocation = allocations.find((allocation) => allocation.id === id);

        if (!allocation) {
          allocation = selectedAllocations.find(
            (allocation) => allocation.id === id
          );
        }

        return allocation;
      });

      setSelectedAllocations(uniqueAllocations);
      setAllChecked(true);
    } else {
      setSelectedAllocations([]);
      setAllChecked(false);
    }
  };

  const isChecked = (allocation) => {
    return selectedAllocations
      .map((allocation) => allocation.id)
      .includes(allocation.id);
  };

  const checkAllHeader = (
    <th key="checkbox" scope="col" className="text-nowrap">
      <input
        type="checkbox"
        name="select_all"
        onChange={onCheckAll}
        value="select_all"
        checked={allChecked}
      />
    </th>
  );

  const inputHeaders = columns.map(({ key, label }) => (
    <th key={key} scope="col" className="text-nowrap">
      <InputLabel
        label={label}
        value={queryState.filters[key]}
        onChange={(value) => queryDispatch({ action: "filter", key, value })}
      />
      <SortButtons
        onClick={(value) =>
          queryDispatch({ action: "sort", key, value: value })
        }
        label={label}
        name={key}
      />
    </th>
  ));

  const emptyHeader = <th key="_"></th>;
  const plainHeaders = [
    emptyHeader,
    ...columns.map(({ key, label }) => (
      <th key={key} scope="col" className="text-nowrap">
        {label}
      </th>
    )),
  ];

  const renderRows = (allocations) => {
    return allocations.map((allocation) => (
      <Row
        key={allocation.id}
        allocation={allocation}
        isChecked={isChecked(allocation)}
        onAllocationCheck={onAllocationCheck}
        columns={columns}
      />
    ));
  };

  return (
    <div className="table-responsive">
      <p className="form-label">Selected {label}:</p>
      <Table
        className="selected-table"
        columns={columns}
        rows={renderRows(selectedAllocations.sort((a, b) => a.id - b.id))}
        headers={plainHeaders}
      />
      <p className="form-label">{label}:</p>
      <PageSelector
        totalPages={totalPages}
        currentPage={queryState.page}
        setCurrentPage={(value) =>
          queryDispatch({ action: "page", key: "page", value })
        }
      />
      <Table
        className="options-table"
        columns={columns}
        rows={renderRows(allocations)}
        headers={[checkAllHeader, ...inputHeaders]}
      />
      <PageSelector
        totalPages={totalPages}
        currentPage={queryState.page}
        setCurrentPage={(value) =>
          queryDispatch({ action: "page", key: "page", value })
        }
      />
    </div>
  );
}

async function getAllocations(params) {
  const PAGE_SIZE = 25;

  const response = await axios.get("/qumulo/api/allocations", {
    params: { ...params, limit: PAGE_SIZE },
  });

  const allocations = response.data.allocations.map((allocation) => ({
    id: allocation.id,
    resources__name: allocation.resources[allocation.resources.length - 1],
    status__name: allocation.status,
    attributes__storage_filesystem_path:
      allocation.attributes.storage_filesystem_path,
  }));

  return { allocations, totalPages: response.data.totalPages };
}

export default AllocationSelector;
