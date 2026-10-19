// GreenLeaf Nexus POS Terminal Engine
(function () {
  let cart = [];
  const config = window.POS_CONFIG || {
    taxRate: 0.05,
    maxDiscount: 30.0,
    checkoutUrl: "/pos/api/checkout",
    currency: "₹"
  };

  // DOM Elements
  const searchInput = document.getElementById("posSearchInput");
  const searchClear = document.getElementById("posSearchClear");
  const categorySelect = document.getElementById("posCategorySelect");
  const categoryPills = document.querySelectorAll(".category-pill-btn");
  const productGrid = document.getElementById("posProductGrid");
  const emptyCatalog = document.getElementById("posEmptyCatalog");
  const productCards = document.querySelectorAll(".pos-product-card");

  const cartItemsList = document.getElementById("posCartItemsList");
  const cartEmptyMessage = document.getElementById("posCartEmptyMessage");
  const btnClearCart = document.getElementById("btnClearCart");
  const discountInput = document.getElementById("posDiscountInput");
  const paymentMethodSelect = document.getElementById("posPaymentMethod");
  const custNameInput = document.getElementById("custName");
  const custPhoneInput = document.getElementById("custPhone");
  const btnCheckout = document.getElementById("btnCheckout");

  const summarySubtotal = document.getElementById("posSummarySubtotal");
  const summaryDiscount = document.getElementById("posSummaryDiscount");
  const discountRow = document.getElementById("posDiscountRow");
  const summaryTax = document.getElementById("posSummaryTax");
  const summaryGrandTotal = document.getElementById("posSummaryGrandTotal");

  // Format currency helper
  function formatMoney(amount) {
    return `${config.currency}${Number(amount).toFixed(2)}`;
  }

  // Filter Catalog
  function filterCatalog() {
    const query = searchInput.value.trim().toLowerCase();
    const category = categorySelect.value.toLowerCase();
    let visibleCount = 0;

    productCards.forEach((card) => {
      const name = (card.getAttribute("data-name") || "").toLowerCase();
      const sku = (card.getAttribute("data-sku") || "").toLowerCase();
      const barcode = (card.getAttribute("data-barcode") || "").toLowerCase();
      const cardCategory = (card.getAttribute("data-category") || "").toLowerCase();

      const matchesQuery = !query || name.includes(query) || sku.includes(query) || barcode.includes(query);
      const matchesCategory = category === "all" || cardCategory === category;

      if (matchesQuery && matchesCategory) {
        card.classList.remove("d-none");
        visibleCount++;
      } else {
        card.classList.add("d-none");
      }
    });

    if (visibleCount === 0) {
      emptyCatalog.classList.remove("d-none");
    } else {
      emptyCatalog.classList.add("d-none");
    }
  }

  // Event Listeners for Search & Filter
  if (searchInput) {
    searchInput.addEventListener("input", filterCatalog);
  }

  if (searchClear) {
    searchClear.addEventListener("click", () => {
      searchInput.value = "";
      filterCatalog();
      searchInput.focus();
    });
  }

  if (categorySelect) {
    categorySelect.addEventListener("change", () => {
      // Sync pill active state
      categoryPills.forEach((p) => {
        p.classList.toggle("active", p.getAttribute("data-category") === categorySelect.value);
      });
      filterCatalog();
    });
  }

  categoryPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      categoryPills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      const cat = pill.getAttribute("data-category");
      categorySelect.value = cat;
      filterCatalog();
    });
  });

  // Add Product to Cart
  productCards.forEach((card) => {
    card.addEventListener("click", () => {
      const productId = parseInt(card.getAttribute("data-id"));
      const name = card.getAttribute("data-name");
      const sku = card.getAttribute("data-sku");
      const price = parseFloat(card.getAttribute("data-price"));
      const stock = parseInt(card.getAttribute("data-stock"));
      const image = card.getAttribute("data-image") || "";

      if (stock <= 0) {
        alert(`'${name}' is currently out of stock.`);
        return;
      }

      const existingIndex = cart.findIndex((item) => item.product_id === productId);
      if (existingIndex > -1) {
        if (cart[existingIndex].quantity < stock) {
          cart[existingIndex].quantity++;
        } else {
          alert(`Cannot add more. Maximum available stock for '${name}' is ${stock}.`);
          return;
        }
      } else {
        cart.push({
          product_id: productId,
          name: name,
          sku: sku,
          price: price,
          stock: stock,
          image: image,
          quantity: 1,
        });
      }

      renderCart();
    });
  });

  // Render Cart Terminal
  function renderCart() {
    if (cart.length === 0) {
      cartItemsList.innerHTML = "";
      cartItemsList.appendChild(cartEmptyMessage);
      cartEmptyMessage.classList.remove("d-none");
      btnCheckout.disabled = true;
      updateSummary(0, 0, 0, 0);
      return;
    }

    cartEmptyMessage.classList.add("d-none");
    btnCheckout.disabled = false;
    cartItemsList.innerHTML = "";

    let subtotal = 0;

    cart.forEach((item, index) => {
      const lineSubtotal = item.price * item.quantity;
      subtotal += lineSubtotal;

      const itemEl = document.createElement("div");
      itemEl.className = "pos-cart-item";
      const imgHtml = item.image
        ? `<img src="${item.image}" alt="${item.name}" class="cart-item-thumb" onerror="this.style.display='none';">`
        : `<div class="cart-item-thumb d-flex align-items-center justify-content-center bg-light text-success"><i class="bi bi-basket"></i></div>`;

      itemEl.innerHTML = `
        ${imgHtml}
        <div class="cart-item-info">
          <div class="cart-item-name" title="${item.name}">${item.name}</div>
          <div class="cart-item-price">${formatMoney(item.price)} each</div>
        </div>
        <div class="cart-qty-controls">
          <button type="button" class="cart-qty-btn btn-minus" data-index="${index}">-</button>
          <span class="cart-qty-val">${item.quantity}</span>
          <button type="button" class="cart-qty-btn btn-plus" data-index="${index}">+</button>
        </div>
        <div class="cart-item-subtotal">${formatMoney(lineSubtotal)}</div>
        <button type="button" class="cart-remove-btn" data-index="${index}" title="Remove item">
          <i class="bi bi-trash"></i>
        </button>
      `;

      cartItemsList.appendChild(itemEl);
    });

    // Attach quantity & remove listeners
    cartItemsList.querySelectorAll(".btn-minus").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt(e.currentTarget.getAttribute("data-index"));
        if (cart[idx].quantity > 1) {
          cart[idx].quantity--;
        } else {
          cart.splice(idx, 1);
        }
        renderCart();
      });
    });

    cartItemsList.querySelectorAll(".btn-plus").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt(e.currentTarget.getAttribute("data-index"));
        if (cart[idx].quantity < cart[idx].stock) {
          cart[idx].quantity++;
        } else {
          alert(`Maximum available stock reached (${cart[idx].stock}).`);
        }
        renderCart();
      });
    });

    cartItemsList.querySelectorAll(".cart-remove-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt(e.currentTarget.getAttribute("data-index"));
        cart.splice(idx, 1);
        renderCart();
      });
    });

    // Calculate Discounts & Taxes
    let discountPct = parseFloat(discountInput.value) || 0;
    if (discountPct < 0) discountPct = 0;
    if (discountPct > config.maxDiscount) {
      discountPct = config.maxDiscount;
      discountInput.value = discountPct;
    }

    const discountAmount = subtotal * (discountPct / 100);
    const taxableAmount = Math.max(0, subtotal - discountAmount);
    const taxAmount = taxableAmount * config.taxRate;
    const grandTotal = taxableAmount + taxAmount;

    updateSummary(subtotal, discountAmount, taxAmount, grandTotal);
  }

  function updateSummary(subtotal, discount, tax, total) {
    summarySubtotal.textContent = formatMoney(subtotal);

    if (discount > 0) {
      discountRow.style.display = "flex";
      summaryDiscount.textContent = `-${formatMoney(discount)}`;
    } else {
      discountRow.style.display = "none";
    }

    summaryTax.textContent = formatMoney(tax);
    summaryGrandTotal.textContent = formatMoney(total);
  }

  // Discount input change
  if (discountInput) {
    discountInput.addEventListener("input", renderCart);
  }

  // Clear Cart
  if (btnClearCart) {
    btnClearCart.addEventListener("click", () => {
      if (cart.length > 0 && confirm("Are you sure you want to clear all items in the cart?")) {
        cart = [];
        renderCart();
      }
    });
  }

  // Checkout API Call
  if (btnCheckout) {
    btnCheckout.addEventListener("click", async () => {
      if (cart.length === 0) {
        alert("Your shopping cart is empty.");
        return;
      }

      btnCheckout.disabled = true;
      btnCheckout.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Processing...`;

      const payload = {
        cart: cart.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
        discount_percent: parseFloat(discountInput.value) || 0,
        payment_method: paymentMethodSelect.value,
        customer_name: custNameInput ? custNameInput.value.trim() : null,
        customer_phone: custPhoneInput ? custPhoneInput.value.trim() : null,
      };

      try {
        const csrfToken = getCsrfToken();
        const response = await fetch(config.checkoutUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify(payload),
        });

        const result = await response.json();

        if (response.ok && result.success) {
          // Update Stock Quantities displayed in catalog locally
          cart.forEach((item) => {
            const card = document.querySelector(`.pos-product-card[data-id="${item.product_id}"]`);
            if (card) {
              const currentStock = parseInt(card.getAttribute("data-stock"));
              const newStock = Math.max(0, currentStock - item.quantity);
              card.setAttribute("data-stock", newStock);
              const stockText = card.querySelector(".pos-card-stock");
              if (stockText) {
                if (newStock > 0) {
                  stockText.textContent = `${newStock} in stock`;
                } else {
                  stockText.innerHTML = `<span class="text-danger fw-bold">Out of stock</span>`;
                  card.classList.add("out-of-stock");
                }
              }
            }
          });

          // Show Success Modal
          document.getElementById("modalInvoiceNum").textContent = result.invoice_number;
          document.getElementById("modalAmountPaid").textContent = formatMoney(result.total_amount);
          document.getElementById("modalBtnReceipt").href = result.receipt_url;

          const modal = new bootstrap.Modal(document.getElementById("checkoutSuccessModal"));
          modal.show();

          // Reset cart & inputs
          cart = [];
          if (discountInput) discountInput.value = "0";
          if (custNameInput) custNameInput.value = "";
          if (custPhoneInput) custPhoneInput.value = "";
          renderCart();
        } else {
          alert(`Checkout failed: ${result.error || "Unknown server error."}`);
        }
      } catch (err) {
        alert(`Checkout connection error: ${err.message}`);
      } finally {
        btnCheckout.disabled = false;
        btnCheckout.innerHTML = `<i class="bi bi-check-circle-fill me-1"></i> Complete Checkout`;
      }
    });
  }

  // Initial render
  renderCart();
})();
