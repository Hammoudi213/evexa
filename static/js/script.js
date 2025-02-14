// Add Product Entry
function addProductEntry() {
    const container = document.getElementById('products-container');
    const template = document.querySelector('.product-entry');
    const newEntry = template.cloneNode(true);

    // Clear input values
    newEntry.querySelectorAll('input').forEach(input => input.value = '');

    // Add remove button if it's not the first entry
    if (container.querySelectorAll('.product-entry').length > 0) {
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-danger mt-2';
        removeBtn.textContent = window.translations?.removeProduct || 'Remove';
        removeBtn.onclick = function() {
            this.parentElement.remove();
        };
        newEntry.appendChild(removeBtn);
    }

    // Setup autocomplete for the new product input
    const productInput = newEntry.querySelector('input[list="product-suggestions"]');
    if (productInput) {
        setupProductAutocomplete(productInput);
    }

    container.appendChild(newEntry);
}

// Show Delivery Details
function showDeliveryDetails(deliveryId) {
    const detailsRow = document.getElementById(`details-${deliveryId}`);
    if (detailsRow) {
        const isVisible = detailsRow.style.display !== 'none';
        detailsRow.style.display = isVisible ? 'none' : 'table-row';
    }
}

// Product name autocomplete
function setupProductAutocomplete(inputElement) {
    inputElement.addEventListener('input', function() {
        const query = this.value;
        if (query.length >= 2) {  // Only fetch suggestions if user typed at least 2 characters
            fetch(`/api/product-suggestions?query=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(products => {
                    const datalist = document.getElementById('product-suggestions');
                    datalist.innerHTML = '';  // Clear existing suggestions
                    products.forEach(product => {
                        const option = document.createElement('option');
                        option.value = product;
                        datalist.appendChild(option);
                    });
                });
        }
    });
}

// Initialize Datepicker and Autocomplete
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners for file inputs
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileName = this.files[0]?.name;
            const label = this.nextElementSibling;
            if (label && fileName) {
                label.textContent = fileName;
            }
        });
    });

    // Setup autocomplete for existing product inputs
    const productInputs = document.querySelectorAll('input[list="product-suggestions"]');
    productInputs.forEach(input => setupProductAutocomplete(input));
});