var updateBtn = document.getElementsByClassName('update-cart');

for (var i = 0; i < updateBtn.length; i++) {
    updateBtn[i].addEventListener('click', function (e) {
        // nếu button nằm trong form, chặn submit để tránh bắn request 2 lần
        e.preventDefault();

        var productId = this.dataset.product;
        var action = this.dataset.action;

        console.log('productId', productId, 'action', action);
        console.log('user:', user);

        // Nếu chưa login
        if (user === "AnonymousUser") {
            console.log('user not logged in');
            return;
        }

        // ✅ lấy qty nếu có (detail page), không có thì = 1
        var qty = 1;
        var qtyInput = document.getElementById('qty-input'); 
        // bạn nhớ đặt id="qty-input" cho ô quantity ở detail.html
        if (qtyInput) {
            qty = parseInt(qtyInput.value || "1");
            if (isNaN(qty) || qty < 1) qty = 1;
            if (qty > 99) qty = 99;
        }

        // Lấy CSRF token (ưu tiên hidden input, fallback cookie)
        var csrfToken = getCSRFToken();
        if (!csrfToken) {
            console.log('Cannot find CSRF token');
            return;
        }

        updateUserOrder(productId, action, qty, csrfToken);
    });
}


// ✅ helper: lấy CSRF từ input hoặc cookie
function getCSRFToken() {
    var csrfTokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfTokenElement) return csrfTokenElement.value;

    // fallback: lấy từ cookie
    var name = 'csrftoken=';
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i].trim();
        if (c.indexOf(name) === 0) {
            return c.substring(name.length, c.length);
        }
    }
    return null;
}


// ✅ Định nghĩa hàm update (có qty)
function updateUserOrder(productId, action, qty, csrfToken) {
    console.log('user login, updating order... qty =', qty);

    var url = '/update_item/';
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            'productId': productId,
            'action': action,
            'qty': qty
        })
    })
    .then((response) => response.json())
    .then((data) => {
        console.log('data', data);
        location.reload();
    })
    .catch((err) => {
        console.log('error', err);
    });
}
