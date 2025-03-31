function initializeModal(containerId, overlayId, modalId, options = {}) {
    const modal = document.getElementById(modalId);
    const overlay = document.getElementById(overlayId);
    const modalContainer = document.getElementById(containerId); // Assuming a fixed container
  
    if (!modal || !overlay || !modalContainer) {
      console.error('Modal or overlay elements not found.');
      return;
    }
  
    const {
      top = '10%',
      left = '10%',
      width = '80%',
      height = '80%',
      maxWidth = '80vw',
      maxHeight = '80vw',
      allowMove = true,
      allowResize = true,
      onClose = () => {}
    } = options;
  
    // Apply initial styles
    modal.style.top = top; // Position will be handled by the container
    modal.style.left = left; // Position will be handled by the container
    modal.style.width = width;
    modal.style.height = height;
    modal.style.maxWidth = maxWidth;
    modal.style.maxHeight = maxHeight;
    modalContainer.style.justifyContent = left === 'center' ? 'center' : (isNaN(parseFloat(left)) ? left : '');
    modalContainer.style.alignItems = top === 'center' ? 'center' : (isNaN(parseFloat(top)) ? top : '');
    if (!isNaN(parseFloat(left))) {
      modalContainer.style.paddingLeft = left;
      modalContainer.style.justifyContent = 'flex-start';
    }
    if (!isNaN(parseFloat(top))) {
      modalContainer.style.paddingTop = top;
      modalContainer.style.alignItems = 'flex-start';
    }
    modalContainer.style.pointerEvents = 'none';
    modal.style.pointerEvents = 'auto';
  
    let isDragging = false;
    let offsetX, offsetY;
  
    if (allowMove) {
      modal.addEventListener('mousedown', (event) => {
        isDragging = true;
        offsetX = event.clientX - modal.getBoundingClientRect().left;
        offsetY = event.clientY - modal.getBoundingClientRect().top;
        modal.style.cursor = 'move';
      });
  
      document.addEventListener('mousemove', (event) => {
        if (isDragging) {
          const newLeft = event.clientX - offsetX;
          const newTop = event.clientY - offsetY;
  
          // Keep modal within viewport (optional, but good practice)
          const viewportWidth = window.innerWidth;
          const viewportHeight = window.innerHeight;
          const modalWidth = modal.offsetWidth;
          const modalHeight = modal.offsetHeight;
  
          modal.style.left = `${Math.max(0, Math.min(newLeft, viewportWidth - modalWidth))}px`;
          modal.style.top = `${Math.max(0, Math.min(newTop, viewportHeight - modalHeight))}px`;
        }
      });
  
      document.addEventListener('mouseup', () => {
        isDragging = false;
        modal.style.cursor = 'default';
      });
    } else {
      modal.style.cursor = 'default'; // Prevent move cursor if not allowed
    }
  
    if (allowResize) {
      const resizeHandles = modal.querySelectorAll('.resize-handle');
      resizeHandles.forEach((handle) => {
        handle.addEventListener('mousedown', (event) => {
          event.stopPropagation(); // Prevent dragging from starting on resize handle
          const modalRect = modal.getBoundingClientRect();
          const isTop = handle.classList.contains('resize-top-right') || handle.classList.contains('resize-top-left');
          const isBottom = handle.classList.contains('resize-bottom-right') || handle.classList.contains('resize-bottom-left');
          const isLeft = handle.classList.contains('resize-bottom-left') || handle.classList.contains('resize-top-left');
          const isRight = handle.classList.contains('resize-bottom-right') || handle.classList.contains('resize-top-right');
  
          document.addEventListener('mousemove', (resizeEvent) => {
            if (isTop) {
              const deltaY = resizeEvent.clientY - modalRect.top;
              modal.style.height = `${modalRect.bottom - resizeEvent.clientY}px`;
              modal.style.top = `${resizeEvent.clientY}px`;
            }
            if (isBottom) {
              modal.style.height = `${resizeEvent.clientY - modalRect.top}px`;
            }
            if (isLeft) {
              const deltaX = resizeEvent.clientX - modalRect.left;
              modal.style.width = `${modalRect.right - resizeEvent.clientX}px`;
              modal.style.left = `${resizeEvent.clientX}px`;
            }
            if (isRight) {
              modal.style.width = `${resizeEvent.clientX - modalRect.left}px`;
            }
          });
  
          const stopResize = () => {
            document.removeEventListener('mousemove', null);
            document.removeEventListener('mouseup', stopResize);
          };
          document.addEventListener('mouseup', stopResize);
        });
      });
    } else {
      const resizeHandles = modal.querySelectorAll('.resize-handle');
      resizeHandles.forEach(handle => handle.style.display = 'none');
    }
  
    const openModal = () => {
      overlay.classList.add('modal-open');
      modalContainer.classList.add('modal-open');
      modal.classList.add('modal-open');
      modalContainer.style.pointerEvents = 'auto';
    };
  
    const closeModal = () => {
      overlay.classList.remove('modal-open');
      modalContainer.classList.remove('modal-open');
      modal.classList.remove('modal-open');
      modalContainer.style.pointerEvents = 'none';
      onClose();
    };
  
    const closeButton = modal.querySelector('#close-modal');
    if (closeButton) {
      closeButton.addEventListener('click', closeModal);
    }
  
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) {
        closeModal();
      }
    });
  
    return { open: openModal, close: closeModal };
  }