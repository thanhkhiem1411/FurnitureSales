document.addEventListener('DOMContentLoaded', function() {
    const updateProfileBtn = document.getElementById('updateProfileBtn');
    updateProfileBtn.addEventListener('click', function() {
        const phoneInput = document.getElementById('phone_number');
        const addressInput = document.getElementById('address');
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        const data = {
            phone_number: phoneInput.value,
            address: addressInput.value
        };

        fetch('/update_profile/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Cập nhật thông tin không thành công');
            }
            return response.json();
        })
        .then(result => {
            alert('Thông tin đã được cập nhật thành công');
            // Cập nhật hiển thị thông tin người dùng trên trang profile nếu cần
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Đã xảy ra lỗi. Vui lòng thử lại sau');
        });
    });
});
