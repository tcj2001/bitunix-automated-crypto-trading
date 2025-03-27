function toggleDropdown() {
    const dropdownContent = document.getElementById("dropdown-content");
    dropdownContent.classList.toggle("show");

    // Adjust the position if the dropdown is near the bottom of the viewport
    const rect = dropdownContent.getBoundingClientRect();
    if (rect.bottom > window.innerHeight) {
        dropdownContent.style.top = `-${rect.height}px`;
    } else {
        dropdownContent.style.top = '100%';
    }
}

function displayNotifications(messages) {
    const lastMessage = document.getElementById("message");
    const dropdownContent = document.getElementById("dropdown-content");

    // Display the last message
    lastMessage.textContent = messages[0];
    // Display the rest of the messages in the dropdown
    dropdownContent.innerHTML = '';
    messages.slice(0).reverse().forEach(message => {
        const div = document.createElement("div");
        div.textContent = message;
        dropdownContent.appendChild(div);
    });
}


// Attach click event to a table and handle cell clicks dynamically
function attachTableClickHandler(tableId, targetColumnIndex, endpoint) {
    const table = document.getElementById(tableId);

    if (!table) {
        console.error(`Table with ID "${tableId}" not found.`);
        return;
    }

    table.addEventListener('click', async (event) => {
        const target = event.target;
        const columnIndex = target.cellIndex;

        // Check if clicked element is a TD and matches the target column index
        if (target.tagName === 'TD' && columnIndex === targetColumnIndex) {
            const row = target.parentNode;

            const headerCell = target
                .closest('table')
                .querySelector(`thead tr th:nth-child(${columnIndex + 1})`);

            const columnName = headerCell ? headerCell.innerText : `Column ${columnIndex + 1}`;
            
            try {
                const symbol = row.cells[targetColumnIndex].innerText;

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `symbol=${encodeURIComponent(symbol)}`, // Sanitize input
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }

                const result = await response.json();
                openURL(result.message); // Call the custom openURL function
            } catch (error) {
                console.error(`Error fetching data for column "${columnName}":`, error);
                alert("An error occurred while processing your request.");
            }
        }
    });
}

// Attach click event to a table and handle cell clicks dynamically
function attachTableClickHandlerFunction(tableId, targetColumnIndex, func) {
    const table = document.getElementById(tableId);

    if (!table) {
        console.error(`Table with ID "${tableId}" not found.`);
        return;
    }

    table.addEventListener('click', async (event) => {
        const target = event.target;
        const columnIndex = target.cellIndex;

        // Check if clicked element is a TD and matches the target column index
        if (target.tagName === 'TD' && columnIndex === targetColumnIndex) {
            const row = target.parentNode;

            const headerCell = target
                .closest('table')
                .querySelector(`thead tr th:nth-child(${columnIndex + 1})`);

            const columnName = headerCell ? headerCell.innerText : `Column ${columnIndex + 1}`;
            const symbol = row.cells[targetColumnIndex].innerText;

            try {
                func(symbol);
            } catch (error) {
                alert("An error occurred while processing your request.");
            }
        }
    });
}

function openURL(url) { 
    window.location.href = url; 
} 

// Batch Save State to Server
async function saveStates(states) {
    let response, data;

    // Send a POST request to /save_states with the states object
    response = await fetch('/save_states', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(states), // Pass the states as a JSON object
    });

    // Parse the response
    data = await response.json();

    // Log the server's response
    console.log(data.message); // Should print "States saved" if successful
}

// Batch Fetch State from Server
async function fetchStates(payload) {
    // Send a POST request to /get_states with the list of element IDs
    const response = await fetch('/get_states', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload), // Pass element IDs in the request body
    });

    // Parse the JSON response
    data = await response.json();

    // Iterate over the states and update the UI elements accordingly
    for (const elementId of payload.element_ids) {
        const state = data.states[elementId] || "No state found";

        if (state !== "No state found") {
            const element = document.getElementById(elementId);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = (state.toString().toLowerCase() === "true");
                } else if (element.tagName === 'SELECT' || element.tagName === 'INPUT') {
                    element.value = state;
                }
            }
        }
    }
}


