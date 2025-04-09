function initializeModal(containerId, overlayId, modalId, options = {}) {
  const modal = document.getElementById(modalId);
  const overlay = document.getElementById(overlayId);
  const modalContainer = document.getElementById(containerId); // Assuming a fixed container
  const resizeHandles = modal.querySelectorAll('.resize-handle');

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

  // get x,y coordinates
  if (allowMove || allowResize) {
    let isDragging = false;
    let offsetX, offsetY;
    let currentResizeHandle = null;
    const resizeHandles = modal.querySelectorAll('.resize-handle');

    // Function to handle mouse move during drag
    const drag = (event) => {
      if (!isDragging || currentResizeHandle) return;
      const newLeft = event.clientX - offsetX;
      const newTop = event.clientY - offsetY;

      // Keep modal within viewport (optional, but good practice)
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const modalWidth = modal.offsetWidth;
      const modalHeight = modal.offsetHeight;

      modal.style.left = `${Math.max(0, Math.min(newLeft, viewportWidth - modalWidth))}px`;
      modal.style.top = `${Math.max(0, Math.min(newTop, viewportHeight - modalHeight))}px`;
    };

    // Function to handle mouse move during resize
    const resize = (event) => {
      if (!currentResizeHandle) return;
      const modalRect = modal.getBoundingClientRect();
      const isTop = currentResizeHandle.classList.contains('resize-top-right') || currentResizeHandle.classList.contains('resize-top-left');
      const isBottom = currentResizeHandle.classList.contains('resize-bottom-right') || currentResizeHandle.classList.contains('resize-bottom-left');
      const isLeft = currentResizeHandle.classList.contains('resize-bottom-left') || currentResizeHandle.classList.contains('resize-top-left');
      const isRight = currentResizeHandle.classList.contains('resize-bottom-right') || currentResizeHandle.classList.contains('resize-top-right');

      if (isTop) {
        const newHeight = modalRect.bottom - event.clientY;
        modal.style.height = `${Math.max(0, newHeight)}px`;
        modal.style.top = `${Math.min(modalRect.bottom - getComputedStyle(modal).minHeight.replace('px', ''), event.clientY)}px`;
      }
      if (isBottom) {
        const newHeight = event.clientY - modalRect.top;
        modal.style.height = `${Math.max(0, newHeight)}px`;
      }
      if (isLeft) {
        const newWidth = modalRect.right - event.clientX;
        modal.style.width = `${Math.max(0, newWidth)}px`;
        modal.style.left = `${Math.min(modalRect.right - getComputedStyle(modal).minWidth.replace('px', ''), event.clientX)}px`;
      }
      if (isRight) {
        const newWidth = event.clientX - modalRect.left;
        modal.style.width = `${Math.max(0, newWidth)}px`;
      }
    };

    // Function to stop dragging/resizing
    const stopInteraction = () => {
      isDragging = false;
      currentResizeHandle = null;
      document.removeEventListener('mousemove', drag);
      document.removeEventListener('mousemove', resize);
      document.removeEventListener('mouseup', stopInteraction);
    };

    // Event listener for mouse down on the modal (for dragging)
    if (allowMove) {
      modal.addEventListener('mousedown', (event) => {
        if (event.target === modal) { // Only start dragging if clicked directly on the modal, not a child
          isDragging = true;
          const modalRect = modal.getBoundingClientRect();
          offsetX = event.clientX - modalRect.left;
          offsetY = event.clientY - modalRect.top;
          document.addEventListener('mousemove', drag);
          document.addEventListener('mouseup', stopInteraction);
        }
      });
    }

    // Event listeners for mouse down on resize handles
    if (allowResize) {
      resizeHandles.forEach((handle) => {
        handle.addEventListener('mousedown', (event) => {
          event.stopPropagation(); // Prevent dragging from starting on resize handle
          currentResizeHandle = handle;
          document.addEventListener('mousemove', resize);
          document.addEventListener('mouseup', stopInteraction);
        });
      });

      // Ensure resize handles are visible when resizing is allowed
      resizeHandles.forEach(handle => handle.style.display = 'block');
    } else {
      // Ensure resize handles are hidden when resizing is not allowed
      resizeHandles.forEach(handle => handle.style.display = 'none');
    }
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
    if (event.target.id === 'modal-container') {
      //closeModal();
    }
  });

  return { open: openModal, close: closeModal };
}

