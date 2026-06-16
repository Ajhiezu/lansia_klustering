/*
main.js - Global UI logic, sidebar toggle, loading screens, and upload indicators
*/

// Show loading overlay
function showLoader(message = 'Memproses data...') {
    const overlay = document.getElementById('loading-overlay');
    const textElement = document.getElementById('loading-text');
    if (overlay) {
        if (textElement) textElement.innerText = message;
        overlay.classList.add('active');
    }
}

// Hide loading overlay
function hideLoader() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // 1. Loading controls for forms
    const formsWithLoader = document.querySelectorAll('form[data-loading-message]');
    formsWithLoader.forEach(form => {
        form.addEventListener('submit', () => {
            const message = form.getAttribute('data-loading-message') || 'Memproses...';
            showLoader(message);
        });
    });

    // 1.5. Sidebar Toggle Logic
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', () => {
            if (window.innerWidth > 992) {
                document.body.classList.toggle('sidebar-collapsed');
            } else {
                document.body.classList.toggle('sidebar-open');
            }
        });
    }

    // 2. Drag & Drop File Upload UI
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileSelectBtn = document.getElementById('file-select-btn');
    const uploadForm = document.getElementById('upload-form');
    const fileInfo = document.getElementById('file-info');
    const selectedFileName = document.getElementById('selected-file-name');

    if (dropZone && fileInput) {
        // Trigger file input click
        if (fileSelectBtn) {
            fileSelectBtn.addEventListener('click', (e) => {
                e.preventDefault();
                fileInput.click();
            });
        }

        // Show selected file name
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                displaySelectedFile(fileInput.files[0]);
            }
        });

        // Dragover state
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        // Dragleave state
        ['dragleave', 'dragend'].forEach(type => {
            dropZone.addEventListener(type, () => {
                dropZone.classList.remove('dragover');
            });
        });

        // Drop event
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
                
                if (['.xlsx', '.csv'].includes(fileExtension)) {
                    fileInput.files = e.dataTransfer.files;
                    displaySelectedFile(file);
                } else {
                    alert('Format file tidak didukung! Gunakan file Excel (.xlsx) atau CSV.');
                }
            }
        });
    }

    function displaySelectedFile(file) {
        if (selectedFileName && fileInfo) {
            selectedFileName.innerText = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            fileInfo.style.display = 'block';
            if (dropZone) {
                dropZone.querySelector('p').innerText = 'File siap diunggah!';
                dropZone.querySelector('i').className = 'fas fa-file-excel fa-3x text-info';
            }
        }
    }

    // 3. Scrollable Table Enhancements (Indicators, Hint, Shift+Scroll)
    const initScrollableTables = () => {
        const tableWrappers = document.querySelectorAll('.table-scroll-wrapper');
        
        tableWrappers.forEach(wrapper => {
            const inner = wrapper.querySelector('.table-scroll-inner');
            const leftIndicator = wrapper.querySelector('.scroll-indicator.left');
            const rightIndicator = wrapper.querySelector('.scroll-indicator.right');
            const hint = wrapper.querySelector('.table-scroll-hint');
            
            if (!inner) return;
            
            const updateIndicators = () => {
                const scrollLeft = inner.scrollLeft;
                const scrollWidth = inner.scrollWidth;
                const clientWidth = inner.clientWidth;
                
                // Only show indicators if table actually overflows horizontally
                const isOverflowing = scrollWidth > clientWidth;
                
                if (isOverflowing) {
                    // Show left indicator if not at start
                    if (leftIndicator) {
                        if (scrollLeft > 5) {
                            leftIndicator.classList.add('visible');
                        } else {
                            leftIndicator.classList.remove('visible');
                        }
                    }
                    
                    // Show right indicator if not at end
                    if (rightIndicator) {
                        if (scrollLeft < scrollWidth - clientWidth - 5) {
                            rightIndicator.classList.add('visible');
                        } else {
                            rightIndicator.classList.remove('visible');
                        }
                    }
                    
                    // Show hint badge
                    if (hint) {
                        hint.classList.add('visible');
                    }
                } else {
                    if (leftIndicator) leftIndicator.classList.remove('visible');
                    if (rightIndicator) rightIndicator.classList.remove('visible');
                    if (hint) hint.classList.remove('visible');
                }
            };
            
            // Listen to scroll events
            inner.addEventListener('scroll', updateIndicators);
            
            // Shift + Mouse Wheel Scroll Support
            inner.addEventListener('wheel', (e) => {
                if (e.deltaY !== 0 && e.shiftKey) {
                    e.preventDefault();
                    inner.scrollLeft += e.deltaY;
                }
            }, { passive: false });
            
            // Initial check after DOM loads and layout stabilizes
            setTimeout(updateIndicators, 100);
            
            // Use ResizeObserver to detect dynamic layout changes (e.g., DataTables initialization)
            if (window.ResizeObserver) {
                const resizeObserver = new ResizeObserver(() => {
                    updateIndicators();
                });
                resizeObserver.observe(inner);
                if (inner.firstElementChild) {
                    resizeObserver.observe(inner.firstElementChild);
                }
            } else {
                window.addEventListener('resize', updateIndicators);
            }
        });
    };

    initScrollableTables();
});
