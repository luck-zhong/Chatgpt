Component({
  properties: {
    item: {
      type: Object,
      value: {}
    }
  },
  methods: {
    onTap() {
      const id = this.data.item._id;
      this.triggerEvent('tap', { id });
    }
  }
});
