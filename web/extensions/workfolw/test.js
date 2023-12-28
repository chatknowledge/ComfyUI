import {app, ComfyApp} from "../../scripts/app.js";

function add_save_workflow_button() {
// 创建按钮容器元素
    var container = document.createElement("div");
    container.classList.add("floating-buttons");
    container.style.position = "fixed";
    container.style.top = "20px";
    container.style.right = "20px";

// 创建按钮1
    var button1 = document.createElement("button");
    button1.innerHTML = "取消";

// 创建按钮2
    var button2 = document.createElement("button");
    button2.innerHTML = "保存工作流";

// 将按钮添加到容器中
    container.appendChild(button1);
    container.appendChild(button2);

// 将容器添加到页面的body元素中
    document.body.appendChild(container);

// 添加按钮1的点击事件监听器
    button1.addEventListener("click", function () {

    });

// 添加按钮2的点击事件监听器
    button2.addEventListener("click", function () {
        Swal.fire({
            width: '600px',
            title: "保存流程",
            html: `
<form>
    <label for="swal-input1">流程名称：</label>
    <input id="swal-input1" class="swal2-input" style="flex-grow: 1; width: 300px;"><br>
    
    <label for="swal-input2">流程描述：</label>
    <textarea id="swal-input2" class="swal2-textarea" rows="5" style="flex-grow: 1; width: 300px;"></textarea><br>
    
</form>
  `,
            showCancelButton: true,
            confirmButtonText: "保存",
        })
    });

}

function checkElementLoaded() {
    var element = document.querySelector(".comfy-menu");
    if (element) {
        // 元素已加载完成，执行修改样式操作
        element.style.display = 'none';
    } else {
        // 元素还未加载完成，继续等待
        setTimeout(checkElementLoaded, 10); // 每100毫秒检查一次
    }
}

// 启动定时器
// checkElementLoaded()
app.registerExtension({
    name: "Comfy.workflows",
    init(app) {
        const urlParams = new URLSearchParams(window.location.search);
        const workflow_id = urlParams.get('workflow_id');
        const tenant_id = urlParams.get('tenant_id');
        let menu = document.querySelector(".comfy-menu");

        const view_type = urlParams.get('view_type');
        if (view_type && view_type === 'add') {
            menu.style.display = 'block';
            add_save_workflow_button()
        } else if (view_type && view_type === 'edit') {
            menu.style.display = 'block';
            add_save_workflow_button()
        }
        if (workflow_id)


            fetch('/comfyui-api/workflow/get_json', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    "workflow_id": workflow_id,
                    "tenant_id": tenant_id ? tenant_id : -1,
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.code !== 0) {
                        Swal.fire({
                            icon: 'error',
                            title: '获取流程失败',
                            text: data.message,
                        })
                        return
                    }
                    // 在这里可以使用获取到的 JSON 数据（data）
                    var filename = "workflow.json";
                    var mimeType = "application/json";

                    var file = new File([data.data], filename, {type: mimeType});
                    app.handleFile(file)
                })
                .catch(error => {
                    // 处理错误
                    console.error(error);
                });

    }
});